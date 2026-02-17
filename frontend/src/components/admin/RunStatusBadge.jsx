const STATUS_STYLES = {
  pending: 'bg-yellow-100 text-yellow-800',
  running: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  cancelled: 'bg-gray-100 text-gray-800',
};

export default function RunStatusBadge({ status }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.pending;

  return (
    <span className={`badge ${style}`}>
      {status}
    </span>
  );
}
