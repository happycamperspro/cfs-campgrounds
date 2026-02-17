import {
  collection,
  query,
  where,
  orderBy,
  limit,
  startAfter,
  getDocs,
  doc,
  getDoc,
} from 'firebase/firestore';

/**
 * Build a Firestore query for browsing campgrounds with filters and pagination.
 *
 * Always filters metadata.isActive == true.
 * Firestore only allows one array-contains per query, so if both siteType and
 * hookup are provided, siteType takes precedence and hookup is left for
 * client-side post-filtering.
 */
export function buildBrowseQuery(
  db,
  { state, region, siteType, hookup, sortBy = 'name', lastDoc: lastDocument, pageSize = 24 } = {}
) {
  const constraints = [];
  const campgroundsRef = collection(db, 'campgrounds');

  // Always filter active campgrounds
  constraints.push(where('metadata.isActive', '==', true));

  // Location filters
  if (state) {
    constraints.push(where('location.state', '==', state));
  }
  if (region) {
    constraints.push(where('location.region', '==', region));
  }

  // Firestore only supports one array-contains per query.
  // Prefer siteType over hookup; the other must be post-filtered client-side.
  let usedArrayContains = false;
  if (siteType) {
    constraints.push(where('details.siteTypes', 'array-contains', siteType));
    usedArrayContains = true;
  }
  if (hookup && !usedArrayContains) {
    constraints.push(where('amenities.hookups', 'array-contains', hookup));
  }

  // Sorting
  switch (sortBy) {
    case 'rating':
      constraints.push(orderBy('ratings.average', 'desc'));
      break;
    case 'recent':
      constraints.push(orderBy('metadata.updatedAt', 'desc'));
      break;
    case 'name':
    default:
      constraints.push(orderBy('name', 'asc'));
      break;
  }

  // Cursor pagination
  if (lastDocument) {
    constraints.push(startAfter(lastDocument));
  }

  // Page size
  constraints.push(limit(pageSize));

  return query(campgroundsRef, ...constraints);
}

/**
 * Build a query to fetch a single campground by its slug.
 */
export function buildSlugQuery(db, slug) {
  const campgroundsRef = collection(db, 'campgrounds');
  return query(
    campgroundsRef,
    where('slug', '==', slug),
    where('metadata.isActive', '==', true),
    limit(1)
  );
}

/**
 * Build a prefix-range search query on the name field.
 * Uses the Unicode trick: name >= searchTerm && name <= searchTerm + '\uf8ff'
 */
export function buildSearchQuery(db, searchTerm, pageSize = 8) {
  const campgroundsRef = collection(db, 'campgrounds');
  return query(
    campgroundsRef,
    where('name', '>=', searchTerm),
    where('name', '<=', searchTerm + '\uf8ff'),
    limit(pageSize)
  );
}
