"""
Firestore loader – writes normalized campground documents to Firestore.

Supports batched upserts with merge semantics, stale-record deactivation,
and dry-run mode for safe testing.
"""

import logging
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, firestore
from tqdm import tqdm

from config.settings import (
    FIREBASE_SERVICE_ACCOUNT_PATH,
    FIRESTORE_BATCH_SIZE,
    FIRESTORE_COLLECTION,
)

logger = logging.getLogger(__name__)


class FirestoreLoader:
    """Batch-oriented Firestore writer for the campground data pipeline."""

    def __init__(self, collection_name=FIRESTORE_COLLECTION, service_account_path=None):
        """Initialise Firebase Admin SDK (idempotent) and Firestore client.

        Args:
            collection_name: Target Firestore collection.
            service_account_path: Path to a service-account JSON key file.
                Falls back to *FIREBASE_SERVICE_ACCOUNT_PATH* from settings,
                then to Application Default Credentials.
        """
        self.collection_name = collection_name
        self._init_firebase(service_account_path)
        self.db = firestore.client()

        # Running totals – reset on each call to upsert_batch
        self.stats = {
            "created": 0,
            "updated": 0,
            "failed": 0,
            "skipped": 0,
        }
        logger.info(
            "FirestoreLoader initialised for collection '%s'", self.collection_name
        )

    # ------------------------------------------------------------------
    # Firebase bootstrap
    # ------------------------------------------------------------------

    @staticmethod
    def _init_firebase(service_account_path=None):
        """Initialise the Firebase Admin SDK exactly once.

        If the default app already exists the call is a no-op.
        """
        if firebase_admin._apps:
            logger.debug("Firebase Admin SDK already initialised – skipping.")
            return

        sa_path = service_account_path or FIREBASE_SERVICE_ACCOUNT_PATH

        if sa_path:
            logger.info("Initialising Firebase with service-account key: %s", sa_path)
            cred = credentials.Certificate(sa_path)
            firebase_admin.initialize_app(cred)
        else:
            logger.info(
                "Initialising Firebase with Application Default Credentials."
            )
            firebase_admin.initialize_app()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upsert_batch(self, records, dry_run=False):
        """Upsert a list of campground records into Firestore.

        Each record **must** contain a ``_doc_id`` key that will be used as
        the Firestore document ID.  Records missing ``_doc_id`` are skipped.

        When updating an existing document the ``ratings`` field and
        ``metadata.createdAt`` are stripped from the payload so that
        user-generated data is never overwritten by the pipeline.

        Args:
            records: Iterable of dicts (normalised campground documents).
            dry_run: If ``True``, log what *would* happen without writing.

        Returns:
            dict with keys ``created``, ``updated``, ``failed``, ``skipped``.
        """
        self.stats = {"created": 0, "updated": 0, "failed": 0, "skipped": 0}

        records = list(records)
        if not records:
            logger.warning("upsert_batch called with an empty record list.")
            return dict(self.stats)

        logger.info(
            "Starting upsert of %d records (dry_run=%s)", len(records), dry_run
        )

        # Pre-fetch existing document IDs to classify create vs update
        existing_ids = self.get_existing_doc_ids()
        logger.info("Found %d existing documents in '%s'", len(existing_ids), self.collection_name)

        collection_ref = self.db.collection(self.collection_name)

        # Process in batches of FIRESTORE_BATCH_SIZE
        for batch_start in tqdm(
            range(0, len(records), FIRESTORE_BATCH_SIZE),
            desc="Firestore upsert",
            unit="batch",
        ):
            batch_slice = records[batch_start : batch_start + FIRESTORE_BATCH_SIZE]
            batch = self.db.batch()
            batch_ops = 0

            for record in batch_slice:
                record = dict(record)  # shallow copy so we don't mutate caller data
                doc_id = record.pop("_doc_id", None)

                if not doc_id:
                    logger.warning("Record missing '_doc_id' – skipping: %s", record.get("name", "<unknown>"))
                    self.stats["skipped"] += 1
                    continue

                cleaned = self._remove_none_values(record)
                is_update = doc_id in existing_ids

                if is_update:
                    # Protect user-generated fields from being overwritten
                    cleaned.pop("ratings", None)
                    metadata = cleaned.get("metadata")
                    if isinstance(metadata, dict):
                        metadata.pop("createdAt", None)

                doc_ref = collection_ref.document(doc_id)

                if dry_run:
                    action = "update" if is_update else "create"
                    logger.debug("[DRY RUN] Would %s doc '%s'", action, doc_id)
                else:
                    batch.set(doc_ref, cleaned, merge=True)
                    batch_ops += 1

                if is_update:
                    self.stats["updated"] += 1
                else:
                    self.stats["created"] += 1

            # Commit the current batch
            if not dry_run and batch_ops > 0:
                try:
                    batch.commit()
                    logger.debug(
                        "Committed batch of %d operations.", batch_ops
                    )
                except Exception:
                    logger.exception(
                        "Failed to commit batch starting at index %d", batch_start
                    )
                    # Mark every record in the failed batch
                    self.stats["failed"] += batch_ops
                    # Undo optimistic counting
                    self.stats["created"] = max(0, self.stats["created"] - batch_ops)
                    self.stats["updated"] = max(0, self.stats["updated"] - batch_ops)

        logger.info(
            "Upsert complete – created: %d, updated: %d, failed: %d, skipped: %d",
            self.stats["created"],
            self.stats["updated"],
            self.stats["failed"],
            self.stats["skipped"],
        )
        return dict(self.stats)

    def get_existing_doc_ids(self):
        """Return a set of all document IDs currently in the collection.

        Uses ``select([])`` so that no field data is transferred – only
        document references are streamed.
        """
        collection_ref = self.db.collection(self.collection_name)
        docs = collection_ref.select([]).stream()
        doc_ids = {doc.id for doc in docs}
        logger.debug("Fetched %d existing doc IDs from '%s'", len(doc_ids), self.collection_name)
        return doc_ids

    def delete_stale_records(self, active_doc_ids, dry_run=False):
        """Soft-delete documents that are no longer present in the pipeline.

        Rather than removing documents outright, stale records have their
        ``metadata.isActive`` flag set to ``False`` and a
        ``metadata.deactivatedAt`` timestamp recorded.

        Args:
            active_doc_ids: Set/collection of document IDs that the current
                pipeline run considers active.
            dry_run: If ``True``, only log – do not write.

        Returns:
            int – number of records deactivated.
        """
        active_doc_ids = set(active_doc_ids)
        existing_ids = self.get_existing_doc_ids()
        stale_ids = existing_ids - active_doc_ids

        if not stale_ids:
            logger.info("No stale records to deactivate.")
            return 0

        logger.info(
            "Found %d stale records to deactivate (dry_run=%s)",
            len(stale_ids),
            dry_run,
        )

        collection_ref = self.db.collection(self.collection_name)
        now = datetime.now(timezone.utc)
        deactivated = 0
        stale_list = sorted(stale_ids)

        for batch_start in tqdm(
            range(0, len(stale_list), FIRESTORE_BATCH_SIZE),
            desc="Deactivating stale records",
            unit="batch",
        ):
            batch_slice = stale_list[batch_start : batch_start + FIRESTORE_BATCH_SIZE]
            batch = self.db.batch()

            for doc_id in batch_slice:
                if dry_run:
                    logger.debug("[DRY RUN] Would deactivate doc '%s'", doc_id)
                else:
                    doc_ref = collection_ref.document(doc_id)
                    batch.update(doc_ref, {
                        "metadata.isActive": False,
                        "metadata.deactivatedAt": now,
                    })

                deactivated += 1

            if not dry_run and batch_slice:
                try:
                    batch.commit()
                    logger.debug(
                        "Committed deactivation batch of %d documents.",
                        len(batch_slice),
                    )
                except Exception:
                    logger.exception(
                        "Failed to commit deactivation batch starting at index %d",
                        batch_start,
                    )
                    deactivated -= len(batch_slice)

        logger.info("Deactivated %d stale records.", deactivated)
        return deactivated

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _remove_none_values(d):
        """Recursively remove keys whose values are ``None`` from *d*.

        Nested dicts are cleaned in-place; other container types (lists,
        tuples) are left untouched.

        Args:
            d: A dict (possibly nested).

        Returns:
            The cleaned dict.
        """
        if not isinstance(d, dict):
            return d

        cleaned = {}
        for key, value in d.items():
            if value is None:
                continue
            if isinstance(value, dict):
                nested = FirestoreLoader._remove_none_values(value)
                if nested:  # skip empty dicts left after pruning
                    cleaned[key] = nested
            else:
                cleaned[key] = value
        return cleaned
