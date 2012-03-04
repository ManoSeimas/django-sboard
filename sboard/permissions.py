class Permission(object):
    def __init__(self, request, action, type=None, name=None, node=None,
                 karma=None):
        self.request = request
        self.action = action
        self.type = type
        self.name = name
        self.node = node
        self.karma = karma

    def __nonzero__(self):
        if self.request.user.is_superuser:
            return True
        elif self.karma is None:
            return False
        else:
            profile = self.request.user.get_profile()
            return profile.karma >= self.karma


class Permissions(object):
    def __init__(self):
        self.permissions = {}

    def update(self, permissions):
        for row in permissions:
            karma = row.pop()
            key = tuple(row)
            self.permissions[key] = karma

    def get_keys(self, action, node):
        return [
            (action, 'owner', None, node),
            (action, 'owner', None, None),

            # TODO: where to get user name?
            #(action, 'user', None, node),
            #(action, 'user', None, None),

            # TODO: get all user groups
            #(action, 'group', None, node),
            #(action, 'group', None, None),

            (action, 'all', None, node),
            (action, 'all', None, None),
        ]

    def can(self, request, action, node):
        for key in self.get_keys(action, node):
            if key in self.permissions:
                params = [request]
                params.extend(key)
                params.append(self.permissions[key])
                return Permission(*params)
        return Permission(request, action, node=node)
