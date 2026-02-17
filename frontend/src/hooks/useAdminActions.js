import { useState, useCallback } from 'react';
import { auth } from '../config/firebase';

/**
 * Resolves the full URL for a Cloud Function endpoint.
 *
 * 2nd Gen Firebase Functions (Python / Cloud Run) have per-function URLs:
 *   https://{function-name}-{base}
 * Set VITE_FUNCTIONS_BASE to the shared suffix (e.g. "goqw44x6gq-uc.a.run.app").
 *
 * Falls back to the legacy 1st Gen pattern if VITE_FUNCTIONS_BASE is not set.
 */
function getFunctionUrl(endpoint) {
  if (import.meta.env.VITE_FUNCTIONS_BASE) {
    const slug = endpoint.replace(/_/g, '-');
    return `https://${slug}-${import.meta.env.VITE_FUNCTIONS_BASE}`;
  }
  if (import.meta.env.VITE_FUNCTIONS_URL) {
    return `${import.meta.env.VITE_FUNCTIONS_URL}/${endpoint}`;
  }
  const projectId = import.meta.env.VITE_FIREBASE_PROJECT_ID || 'hcp-social-chat-firebase-host';
  return `https://us-central1-${projectId}.cloudfunctions.net/${endpoint}`;
}

/**
 * Makes an authenticated POST request to a Cloud Function.
 */
async function authenticatedPost(endpoint, body) {
  const currentUser = auth.currentUser;
  if (!currentUser) {
    throw new Error('User must be authenticated to perform admin actions');
  }

  const token = await currentUser.getIdToken();
  const url = getFunctionUrl(endpoint);

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Request failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Hook that wraps fetch calls to Cloud Functions for admin scraper operations.
 *
 * @returns {{
 *   triggerScraper: Function,
 *   cancelScraper: Function,
 *   updateConfig: Function,
 *   loading: boolean,
 *   error: Error|null
 * }}
 */
export function useAdminActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const triggerScraper = useCallback(async (spiderName, options = {}) => {
    setLoading(true);
    setError(null);

    try {
      const result = await authenticatedPost('trigger_scraper', {
        spiderName,
        targetStates: options.targetStates || null,
        itemLimit: options.itemLimit || null,
      });
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const cancelScraper = useCallback(async (runId) => {
    setLoading(true);
    setError(null);

    try {
      const result = await authenticatedPost('cancel_scraper', { runId });
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateConfig = useCallback(async (spiderName, fields) => {
    setLoading(true);
    setError(null);

    try {
      const result = await authenticatedPost('update_scraper_config', {
        spiderName,
        ...fields,
      });
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { triggerScraper, runSpider: triggerScraper, cancelScraper, updateConfig, loading, running: loading, error };
}
