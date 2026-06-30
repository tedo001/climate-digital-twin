"""Storage layer: DuckDB persistence and file-based caches.

Owns all disk I/O for state versions, dataset manifests, and caches; the
only layer permitted to talk directly to the filesystem/DuckDB (SAD Section 1).
"""
