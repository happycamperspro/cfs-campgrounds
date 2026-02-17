export default function EmptyState({
  title = 'No campgrounds found',
  message = 'Try adjusting your filters or search to find what you are looking for.',
}) {
  return (
    <div className="text-center py-16 px-4">
      {/* Tent / campground icon */}
      <svg
        className="mx-auto h-16 w-16 text-gray-300 mb-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 3L2 20h20L12 3z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 16v4"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9.5 20L12 14l2.5 6"
        />
      </svg>
      <h3 className="text-lg font-semibold text-gray-700 mb-2">{title}</h3>
      <p className="text-sm text-gray-500 max-w-md mx-auto">{message}</p>
    </div>
  );
}
