export function Silhouette({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden
      role="img"
    >
      <path d="M12 12a4.5 4.5 0 1 0-4.5-4.5A4.5 4.5 0 0 0 12 12Zm0 2c-4.5 0-8 2.7-8 6v2h16v-2c0-3.3-3.5-6-8-6Z" />
    </svg>
  );
}
