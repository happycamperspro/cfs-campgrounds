export default function AmenityBadge({ label, icon }) {
  return (
    <span className="badge bg-green-50 text-green-700 border border-green-200">
      {icon && <span className="mr-1">{icon}</span>}
      {label}
    </span>
  );
}
