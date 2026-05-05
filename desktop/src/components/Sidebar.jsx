export default function Sidebar({
  isOpen,
  onClose,
  currentUser,
  solvedProblems,
  workingDir,
  onOpenUserModal,
  onSelectWorkingDirectory,
}) {
  const displayDir = workingDir
    ? workingDir.split(/[\\/]/).pop() || workingDir
    : null

  return (
    <>
      <div className={`sidebar-overlay ${isOpen ? 'open' : ''}`} onClick={onClose} />
      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        {/* ── App name ─────────────────────────── */}
      <div className="sidebar-brand">
        <div className="sidebar-logo">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
              stroke="url(#g1)"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <defs>
              <linearGradient id="g1" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                <stop stopColor="#38bdf8" />
                <stop offset="1" stopColor="#818cf8" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <span className="sidebar-app-name">Agentic CPH</span>
      </div>

      {/* ── Recently solved ──────────────────── */}
      <div className="sidebar-section sidebar-solved">
        <p className="sidebar-section-label">Recently Solved</p>
        <ul className="sidebar-problem-list">
          {solvedProblems.length === 0 ? (
            <li className="sidebar-empty">No problems solved yet</li>
          ) : (
            solvedProblems.slice(0, 15).map((p) => (
              <li key={p.id ?? p.problem_id} className="sidebar-problem-item">
                <span className="sidebar-problem-id">{p.problem_id}</span>
                <span className="sidebar-problem-title" title={p.title}>
                  {p.title || p.problem_id}
                </span>
                {p.rating && (
                  <span
                    className={`sidebar-rating ${
                      p.rating <= 1200 ? 'easy' : p.rating <= 1700 ? 'medium' : 'hard'
                    }`}
                  >
                    {p.rating}
                  </span>
                )}
              </li>
            ))
          )}
        </ul>
      </div>

      {/* ── Footer: working dir + user ────────── */}
      <div className="sidebar-footer">
        {/* Working directory */}
        <button
          type="button"
          className="sidebar-dir-btn"
          onClick={onSelectWorkingDirectory}
          title={workingDir || 'No folder selected'}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinejoin="round"
            />
          </svg>
          <span className="sidebar-dir-text">{displayDir || 'Open folder…'}</span>
        </button>

        {/* User row */}
        <button
          type="button"
          className="sidebar-user-btn"
          onClick={onOpenUserModal}
          title={currentUser ? `Switch user (${currentUser.username})` : 'Select or create user'}
        >
          <div className="sidebar-avatar">
            {currentUser ? currentUser.username.charAt(0).toUpperCase() : '?'}
          </div>
          <div className="sidebar-user-info">
            <span className="sidebar-username">
              {currentUser ? currentUser.username : 'No user'}
            </span>
            {currentUser && (
              <span className="sidebar-user-stat">
                {currentUser.stats?.problems_solved ?? 0} solved
              </span>
            )}
          </div>
          <svg
            className="sidebar-chevron"
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M9 18l6-6-6-6"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>
    </aside>
    </>
  )
}
