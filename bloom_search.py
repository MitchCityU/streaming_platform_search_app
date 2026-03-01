import hashlib
import math


class BloomFilter:
    """
    Simple Bloom filter.

    Functionality:
    - Stores membership information using a bit array.
    - Uses multiple hash functions to set bits.
    - Can quickly determine if an item is:
        • Definitely NOT present
        • Possibly present (may have false positives)
    """

    def __init__(self, expected_items, false_positive_rate=0.01):
        # Ensure at least 1 expected item
        if expected_items < 1:
            expected_items = 1

        # Calculate size of bit array (m)
        numerator = -(expected_items * math.log(false_positive_rate))
        denominator = (math.log(2) ** 2)
        m_value = numerator / denominator
        m = int(m_value)

        if m < 64:
            m = 64

        self.m = m

        # Calculate number of hash functions (k)
        k_value = (self.m / expected_items) * math.log(2)
        k = int(k_value)

        if k < 2:
            k = 2

        self.k = k

        # Bit storage (single integer used as bit array)
        self.bits = 0

    def hashes(self, item):
        """
        Generate k hash indexes for the item.
        Uses double hashing technique.
        """
        encoded = item.encode("utf-8")

        sha_hash = hashlib.sha256(encoded).hexdigest()
        md5_hash = hashlib.md5(encoded).hexdigest()

        h1 = int(sha_hash, 16)
        h2 = int(md5_hash, 16)

        indexes = []

        i = 0
        while i < self.k:
            combined_hash = h1 + (i * h2)
            index = combined_hash % self.m
            indexes.append(index)
            i += 1

        return indexes

    def add(self, item):
        """
        Add an item to the Bloom filter.
        """
        hash_indexes = self.hashes(item)

        i = 0
        while i < len(hash_indexes):
            index = hash_indexes[i]

            # Set the bit at position 'index'
            self.bits = self.bits | (1 << index)

            i += 1

    def might_contain(self, item):
        """
        Check if item might exist in the filter.
        Returns:
            False = Definitely not present
            True  = Possibly present
        """
        hash_indexes = self.hashes(item)

        i = 0
        while i < len(hash_indexes):
            index = hash_indexes[i]

            # Check if bit is set
            if (self.bits & (1 << index)) == 0:
                return False

            i += 1

        return True


class BloomFilterSearch:
    """
    Bloom-filter-assisted exact Title search.

    Steps:
    1. Uses BloomFilter for fast rejection.
    2. Uses dictionary lookup to eliminate false positives.
    3. Returns record IDs along with status message.
    """

    def __init__(self, false_positive_rate=0.01):
        self.false_positive_rate = false_positive_rate
        self.bloom = None
        self.title_to_ids = {}

    def build(self, items):
        """
        Build Bloom filter and exact lookup dictionary.
        """
        expected_count = len(items)

        self.bloom = BloomFilter(expected_count, self.false_positive_rate)

        self.title_to_ids.clear()

        i = 0
        while i < len(items):
            record_id = items[i][0]
            title = items[i][1]

            key = title
            if key is None:
                key = ""

            key = key.strip().lower()

            if key != "":
                self.bloom.add(key)

                if key not in self.title_to_ids:
                    self.title_to_ids[key] = []

                self.title_to_ids[key].append(record_id)

            i += 1

    def search(self, title):
        """
        Search for an exact title.
        """
        if self.bloom is None:
            raise RuntimeError("BloomFilterSearch not built. Call build() first.")

        key = title
        if key is None:
            key = ""

        key = key.strip().lower()

        if key == "":
            return ([], "Empty title query.")

        # Fast rejection
        if not self.bloom.might_contain(key):
            return ([], "Bloom says DEFINITELY NOT present.")

        # Exact lookup to avoid false positives
        if key in self.title_to_ids:
            ids = self.title_to_ids[key]
            return (ids, "Bloom says MAYBE; exact lookup FOUND matches.")

        return ([], "Bloom says MAYBE; exact lookup found 0 (false positive).")
