export const US_STATES = {
  AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas',
  CA: 'California', CO: 'Colorado', CT: 'Connecticut', DE: 'Delaware',
  FL: 'Florida', GA: 'Georgia', HI: 'Hawaii', ID: 'Idaho',
  IL: 'Illinois', IN: 'Indiana', IA: 'Iowa', KS: 'Kansas',
  KY: 'Kentucky', LA: 'Louisiana', ME: 'Maine', MD: 'Maryland',
  MA: 'Massachusetts', MI: 'Michigan', MN: 'Minnesota', MS: 'Mississippi',
  MO: 'Missouri', MT: 'Montana', NE: 'Nebraska', NV: 'Nevada',
  NH: 'New Hampshire', NJ: 'New Jersey', NM: 'New Mexico', NY: 'New York',
  NC: 'North Carolina', ND: 'North Dakota', OH: 'Ohio', OK: 'Oklahoma',
  OR: 'Oregon', PA: 'Pennsylvania', RI: 'Rhode Island', SC: 'South Carolina',
  SD: 'South Dakota', TN: 'Tennessee', TX: 'Texas', UT: 'Utah',
  VT: 'Vermont', VA: 'Virginia', WA: 'Washington', WV: 'West Virginia',
  WI: 'Wisconsin', WY: 'Wyoming',
};

export const REGIONS = {
  'Northeast': ['CT', 'DE', 'ME', 'MD', 'MA', 'NH', 'NJ', 'NY', 'PA', 'RI', 'VT'],
  'Southeast': ['AL', 'AR', 'FL', 'GA', 'KY', 'LA', 'MS', 'NC', 'SC', 'TN', 'VA', 'WV'],
  'Midwest': ['IL', 'IN', 'IA', 'KS', 'MI', 'MN', 'MO', 'NE', 'ND', 'OH', 'SD', 'WI'],
  'Southwest': ['AZ', 'NM', 'OK', 'TX'],
  'Rocky Mountain': ['CO', 'ID', 'MT', 'UT', 'WY'],
  'Pacific Northwest': ['OR', 'WA'],
  'Pacific': ['CA', 'HI', 'NV'],
  'Alaska': ['AK'],
};

export const SITE_TYPES = [
  { value: 'tent', label: 'Tent' },
  { value: 'rv', label: 'RV' },
  { value: 'cabin', label: 'Cabin' },
  { value: 'yurt', label: 'Yurt' },
  { value: 'glamping', label: 'Glamping' },
  { value: 'group', label: 'Group Site' },
];

export const HOOKUP_TYPES = [
  { value: 'electric', label: 'Electric' },
  { value: 'water', label: 'Water' },
  { value: 'sewer', label: 'Sewer' },
];

export const FACILITY_TYPES = [
  { value: 'restrooms', label: 'Restrooms' },
  { value: 'showers', label: 'Showers' },
  { value: 'laundry', label: 'Laundry' },
  { value: 'store', label: 'Camp Store' },
  { value: 'wifi', label: 'WiFi' },
  { value: 'dump_station', label: 'Dump Station' },
];

export const ACTIVITY_TYPES = [
  { value: 'hiking', label: 'Hiking' },
  { value: 'fishing', label: 'Fishing' },
  { value: 'swimming', label: 'Swimming' },
  { value: 'boating', label: 'Boating' },
  { value: 'biking', label: 'Biking' },
  { value: 'wildlife', label: 'Wildlife Viewing' },
];

export const SORT_OPTIONS = [
  { value: 'name', label: 'Name (A-Z)' },
  { value: 'rating', label: 'Highest Rated' },
  { value: 'recent', label: 'Recently Updated' },
];

export const SOURCE_LABELS = {
  recreation_gov: 'Recreation.gov',
  nps: 'National Park Service',
  koa: 'KOA',
  hipcamp: 'Hipcamp',
  good_sam: 'Good Sam',
  thousand_trails: 'Thousand Trails',
  state_parks: 'State Parks',
};

export const SOURCE_COLORS = {
  recreation_gov: 'bg-green-100 text-green-800',
  nps: 'bg-amber-100 text-amber-800',
  koa: 'bg-yellow-100 text-yellow-800',
  hipcamp: 'bg-emerald-100 text-emerald-800',
  good_sam: 'bg-blue-100 text-blue-800',
  thousand_trails: 'bg-purple-100 text-purple-800',
  state_parks: 'bg-teal-100 text-teal-800',
};

export const PAGE_SIZE = 24;
