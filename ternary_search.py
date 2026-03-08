from dataclasses import dataclass, field


@dataclass(slots=True)
class TSTNode:
    """
    Node in a Ternary Search Tree.
    """
    char: str
    left: "TSTNode | None" = None
    mid: "TSTNode | None" = None
    right: "TSTNode | None" = None
    is_end: bool = False
    record_ids: set = field(default_factory=set)


class TernarySearch:
    """
    Ternary Search Tree (TST) used for prefix searching.

    Improvements over the basic version:
    - iterative insert/get/search traversal to avoid recursion overhead
    - deduplicated record IDs using a set
    - prefix-search result caching for repeated queries
    - configurable normalization
    """

    def __init__(self, normalize_case=True, cache_size=256):
        self.root = None
        self.normalize_case = normalize_case
        self.cache_size = cache_size
        self._cache = {}
        self._cache_order = []
        self._version = 0

    def _normalize(self, key):
        """
        Normalize user input before inserting/searching.
        """
        if key is None:
            return ""

        key = key.strip()
        if self.normalize_case:
            key = key.lower()

        return key

    def _clear_cache(self):
        """
        Invalidate prefix cache after inserts.
        """
        self._cache.clear()
        self._cache_order.clear()

    def _cache_get(self, prefix, limit):
        """
        Return cached prefix-search result if valid.
        """
        cache_key = (prefix, limit, self._version)
        return self._cache.get(cache_key)

    def _cache_set(self, prefix, limit, result):
        """
        Store prefix-search result in a small FIFO cache.
        """
        cache_key = (prefix, limit, self._version)

        if cache_key in self._cache:
            return

        if len(self._cache_order) >= self.cache_size:
            oldest = self._cache_order.pop(0)
            self._cache.pop(oldest, None)

        self._cache[cache_key] = result
        self._cache_order.append(cache_key)

    def insert(self, key, record_id):
        """
        Insert a key and associated record_id into the tree.

        Iterative version to avoid recursion overhead.
        """
        key = self._normalize(key)
        if key == "":
            return

        if self.root is None:
            self.root = TSTNode(key[0])

        node = self.root
        index = 0

        while True:
            current_char = key[index]

            if current_char < node.char:
                if node.left is None:
                    node.left = TSTNode(current_char)
                node = node.left

            elif current_char > node.char:
                if node.right is None:
                    node.right = TSTNode(current_char)
                node = node.right

            else:
                # Character matches
                if index == len(key) - 1:
                    node.is_end = True
                    node.record_ids.add(record_id)
                    self._version += 1
                    self._clear_cache()
                    return

                index += 1
                next_char = key[index]

                if node.mid is None:
                    node.mid = TSTNode(next_char)

                node = node.mid

    def get_node(self, key):
        """
        Iteratively navigate to the node for the last character of key.
        """
        key = self._normalize(key)

        if key == "" or self.root is None:
            return None

        node = self.root
        index = 0

        while node is not None:
            current_char = key[index]

            if current_char < node.char:
                node = node.left

            elif current_char > node.char:
                node = node.right

            else:
                if index == len(key) - 1:
                    return node

                index += 1
                node = node.mid

        return None

    def prefix_search(self, prefix, limit=50):
        """
        Return record_ids for keys that start with 'prefix'.

        Uses caching to speed up repeated searches.
        """
        prefix = self._normalize(prefix)

        if prefix == "" or self.root is None or limit <= 0:
            return []

        cached = self._cache_get(prefix, limit)
        if cached is not None:
            return list(cached)

        node = self.get_node(prefix)
        if node is None:
            return []

        matches = []

        # If the prefix itself is a full key, include its IDs first.
        if node.is_end and node.record_ids:
            for record_id in node.record_ids:
                matches.append(record_id)
                if len(matches) >= limit:
                    result = matches[:limit]
                    self._cache_set(prefix, limit, tuple(result))
                    return result

        # Collect descendants iteratively from node.mid
        self.collect_iterative(node.mid, matches, limit)

        result = matches[:limit]
        self._cache_set(prefix, limit, tuple(result))
        return result

    def collect_iterative(self, start_node, output_list, limit):
        """
        Iteratively collect record_ids from subtree starting at start_node.

        Traversal order is equivalent to:
        - left
        - current
        - mid
        - right

        Uses an explicit stack instead of recursion.
        """
        if start_node is None or len(output_list) >= limit:
            return

        stack = [(start_node, 0)]

        while stack and len(output_list) < limit:
            node, state = stack.pop()

            if node is None:
                continue

            if state == 0:
                # Simulate recursive DFS:
                # collect(left), visit(node), collect(mid), collect(right)
                stack.append((node, 3))       # after mid -> do right
                stack.append((node.mid, 0))   # traverse mid
                stack.append((node, 1))       # visit node
                stack.append((node.left, 0))  # traverse left

            elif state == 1:
                if node.is_end and node.record_ids:
                    for record_id in node.record_ids:
                        output_list.append(record_id)
                        if len(output_list) >= limit:
                            return

            elif state == 3:
                stack.append((node.right, 0))
