import AmenityBadge from './AmenityBadge';

function AmenitySection({ title, items }) {
  if (!items || items.length === 0) return null;

  return (
    <div className="mb-4">
      <h4 className="text-sm font-semibold text-gray-600 mb-2">{title}</h4>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <AmenityBadge key={item} label={item} />
        ))}
      </div>
    </div>
  );
}

export default function AmenityList({ hookups, facilities, activities }) {
  const hasAny =
    (hookups && hookups.length > 0) ||
    (facilities && facilities.length > 0) ||
    (activities && activities.length > 0);

  if (!hasAny) return null;

  return (
    <div>
      <AmenitySection title="Hookups" items={hookups} />
      <AmenitySection title="Facilities" items={facilities} />
      <AmenitySection title="Activities" items={activities} />
    </div>
  );
}
