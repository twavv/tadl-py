# Twavv's Awesome Data Loader

This is a small, experimental package that implements an extended [DataLoader](https://github.com/graphql/dataloader) pattern.

It's designed to make it easier to manage data loaders that can fetch data based on different attributes of the data while managing cache coherency between dataloaders.

## Background

A data loader is a very common pattern for loading data, especially when building GraphQL APIs.

In general, a data loader is a function that loads an object based on some key (like a database ID) and batches and caches multiple calls together under the hood. A simple data loader looks something like this:

```ts
const userLoader = new DataLoader(async (ids: number[]) => {
  const users = await db.query(
    `SELECT * FROM users WHERE id IN $?;`,
    [ids],
  );
  // DataLoader requires results to be returned as an array in the exact same
  // order as the input array.
  return ids.map(id => users.find(user => user.id === id));
});

// Multiple calls to userLoader.load will be batched together under
// the hood and result in a single query to the database.
const users = await Promise.all([
    userLoader.load(1),
    userLoader.load(2),
    userLoader.load(3),
]);
```

This can become more complicated in practice when we need to load database based on things other than the database ID. For example, we might want to load a user based on their email address:

```ts
const userLoaderByEmail = new DataLoader(async (emails: string[]) => {
    const users = await db.query(
        `SELECT * FROM users WHERE email IN $?;`,
        [emails],
    );
    return ids.map(id => users.find(user => user.id === id));
});
```

We might also need to load a group of users based on some criteria (such as their membership in a group):
```ts
const userLoaderByGroup = new DataLoader(async (groupIds: number[]) => {
  const users = await db.query(
    `SELECT * FROM users WHERE group_id IN $?;`,
    [groupIds]
  );
  return groupIds.map(groupId => users.filter(user => user.groupId === groupId));
});
```

With this approach, we're not sharing data between the data loaders. If we load a user by ID and then by email, we'll end up with two separate copies of the user in memory (which can be important for some use cases).

One solution to this problem is to wire your dataloaders together so that a call to one dataloader also primes the other. This logic ends up being spread out, adds more layers of indirection, and is generally tedious to write:

```ts
const userLoader = new DataLoader(async (ids: number[]) => {
    const users = await db.query(
        `SELECT * FROM users WHERE id IN $?;`,
        [ids],
    );
    // Prime the other data loaders
    for (const user of users) {
        userLoaderByEmail.prime(user.email, user);
    }
    return ids.map(id => users.find(user => user.id === id));
});
const userLoaderByEmail = new DataLoader(async (emails: string[]) => {
    const users = await db.query(
        `SELECT * FROM users WHERE email IN $?;`,
        [emails],
    );
    // Prime the other data loaders
    for (const user of users) {
        userLoader.prime(user.id, user);
    }
    return ids.map(id => users.find(user => user.id === id));
});
const userLoaderByGroup = new DataLoader(async (groupIds: number[]) => {
    const users = await db.query(
        `SELECT * FROM users WHERE group_id IN $?;`,
        [groupIds]
    );
    // Prime the other data loaders
    for (const user of users) {
        userLoader.prime(user.id, user);
        userLoaderByEmail.prime(user.email, user);
    }
    return groupIds.map(groupId => users.filter(user => user.groupId === groupId));
});
```

## TADL's Approach

With TADL, we define a single **query** function (that loads data based on arbitrary criteria) and several **interfaces** to that query. Each interface defines a way to load data based on a different set of criteria.

For the example use case above:
```python
import tadl

class UserService:
    @tadl.query
    async def __query_users(self, filter: tuple[str, list[str] | list[int]]) -> list[User]:
        column, values = filter
        # IMPORTANT:
        # THIS IS A SIMPLIFIED EXAMPLE. DO NOT USE STRING INTERPOLATION WITH
        # SQL QUERIES IN PRODUCTION CODE.
        users_data = await db.query(f"SELECT * FROM users WHERE ${column} IN ${values};")
        
        # The query function can perform arbitrary transformations, add extra
        # filters, do privacy/authorization checks, etc.
        # Unlike the example above, the results can be in any order and the TADL
        # machinery will take care of ordering based on the key specified in the
        # interface definition.
        return [
            User(**data)
            for data in users_data
        ]
    
    # A batch interface returns a single item for every input key.
    @__query_users.batch_interface(key=lambda user: user.id)
    async def by_id(self, ids: list[int]) -> list[User | None]:
        return await self.__query_users(("id", ids))

    @__query_users.batch_interface(key=lambda user: user.email)
    async def by_email(self, emails: list[str]) -> list[User | None]:
        return await self.__query_users(("email", emails))

    # A group interface returns a list of items for every input key.
    # The results are sorted based on the provided sort function to ensure that
    # the output has a deterministic order.
    @__query_users.group_interface(
        key=lambda user: user.group_id,
        sort=lambda user: user.id,
    )
    async def by_group(self, group_ids: list[int]) -> list[list[User]]:
        return await self.__query_users(("group_id", group_ids))
```

With this setup, we can load a user by ID, email, or group ID and the TADL machinery will take care of caching and cache coherency between the different interfaces.

```python
# Our database looks like:
#   - User(id=1, email="user1@example.com", group_id=1)
#   - User(id=2, email="user2@example.com", group_id=1)
#   - User(id=3, email="user3@example.com", group_id=2)

svc = UserService()

# Load a user by ID.
# This results in a single database query.
user_one = await svc.by_id(1)

# Load a user by email.
# This does not result in a database query because the user was already loaded
# and primed into the `by_email` loader.
user_one = await svc.by_email("user1@example.com")

# Load many users.
# This results in a single database query to load user 2 (user 1 is already
# cached and won't be queried again).
user_one, user_two = await svc.by_id.load_many([1, 2])

# Load a group of users.
# This results in a single database query. While we have loaded both user 1 and
# user 2, who both belong to group 1, we still need to issue another database 
# query to make sure we load all the users in group 1 (not just the ones that 
# happen to have been primed in our database). 
group_one = await svc.by_group(1)
```