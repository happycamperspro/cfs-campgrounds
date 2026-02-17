import { useState, useCallback } from 'react';

/**
 * Generic cursor-based pagination hook.
 *
 * @param {Function} fetchFn  - Async function (lastDoc) => { items: [], lastDoc: snapshot|null }
 * @param {number}   pageSize - Number of items per page.
 * @returns {{ items, loading, error, loadMore, hasMore, reset }}
 */
export function usePagination(fetchFn, pageSize) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastDoc, setLastDoc] = useState(null);
  const [hasMore, setHasMore] = useState(true);

  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;

    setLoading(true);
    setError(null);

    try {
      const result = await fetchFn(lastDoc);
      const newItems = result.items || [];

      setItems((prev) => [...prev, ...newItems]);
      setLastDoc(result.lastDoc || null);
      setHasMore(newItems.length >= pageSize);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [fetchFn, lastDoc, loading, hasMore, pageSize]);

  const reset = useCallback(() => {
    setItems([]);
    setLastDoc(null);
    setHasMore(true);
    setError(null);
    setLoading(false);
  }, []);

  return { items, loading, error, loadMore, hasMore, reset };
}
