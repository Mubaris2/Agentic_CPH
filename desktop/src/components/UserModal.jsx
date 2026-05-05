import { useState } from 'react'

const TOPIC_OPTIONS = [
  'dp', 'greedy', 'graphs', 'binary search', 'two pointers',
  'math', 'strings', 'trees', 'data structures', 'constructive',
  'number theory', 'geometry', 'brute force', 'segment tree', 'bitmask',
]

function TagSelector({ label, selected, onChange }) {
  function toggle(tag) {
    if (selected.includes(tag)) {
      onChange(selected.filter((t) => t !== tag))
    } else {
      onChange([...selected, tag])
    }
  }

  return (
    <div className="tag-selector">
      <p className="um-field-label">{label}</p>
      <div className="tag-selector-grid">
        {TOPIC_OPTIONS.map((tag) => (
          <button
            key={tag}
            type="button"
            className={`tag-chip ${selected.includes(tag) ? 'selected' : ''}`}
            onClick={() => toggle(tag)}
          >
            {tag}
          </button>
        ))}
      </div>
    </div>
  )
}

function CreateView({ onCreated, apiBase }) {
  const [name, setName] = useState('')
  const [strengths, setStrengths] = useState([])
  const [weaknesses, setWeaknesses] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleCreate() {
    const username = name.trim()
    if (!username) { setError('Username is required.'); return }
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${apiBase}/api/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username }),
      })
      if (res.status === 409) { setError('Username already taken.'); return }
      if (!res.ok) throw new Error('Failed to create user')
      const data = await res.json()
      let user = data.user

      // Save strengths/weaknesses if set
      if (strengths.length || weaknesses.length) {
        const upRes = await fetch(`${apiBase}/api/users/${user.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ strengths, weaknesses }),
        })
        if (upRes.ok) {
          const upData = await upRes.json()
          user = upData.user
        }
      }

      onCreated(user)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="um-create">
      <p className="um-field-label">Username</p>
      <input
        className="um-input"
        placeholder="e.g. alice"
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
        autoFocus
      />

      <TagSelector label="Strengths" selected={strengths} onChange={setStrengths} />
      <TagSelector label="Weaknesses" selected={weaknesses} onChange={setWeaknesses} />

      {error && <p className="um-error">{error}</p>}
      <button
        type="button"
        className="um-btn primary"
        onClick={handleCreate}
        disabled={loading}
      >
        {loading ? 'Creating…' : 'Create Profile'}
      </button>
    </div>
  )
}

function EditView({ user, apiBase, onSaved }) {
  const [strengths, setStrengths] = useState(user.strengths ?? [])
  const [weaknesses, setWeaknesses] = useState(user.weaknesses ?? [])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSave() {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${apiBase}/api/users/${user.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strengths, weaknesses }),
      })
      if (!res.ok) throw new Error('Failed to save')
      const data = await res.json()
      onSaved(data.user)
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="um-create">
      <p className="um-section-title">Editing: {user.username}</p>
      <TagSelector label="Strengths" selected={strengths} onChange={setStrengths} />
      <TagSelector label="Weaknesses" selected={weaknesses} onChange={setWeaknesses} />
      {error && <p className="um-error">{error}</p>}
      <button
        type="button"
        className="um-btn primary"
        onClick={handleSave}
        disabled={loading}
      >
        {loading ? 'Saving…' : 'Save'}
      </button>
    </div>
  )
}

export default function UserModal({ isOpen, onClose, currentUser, onSelectUser, apiBase }) {
  const [tab, setTab] = useState('list')   // 'list' | 'create' | 'edit'
  const [users, setUsers] = useState(null)  // null = not yet loaded
  const [editTarget, setEditTarget] = useState(null)
  const [listLoading, setListLoading] = useState(false)

  async function loadUsers() {
    setListLoading(true)
    try {
      const res = await fetch(`${apiBase}/api/users`)
      const data = await res.json()
      setUsers(data.users || [])
    } catch {
      setUsers([])
    } finally {
      setListLoading(false)
    }
  }

  // Load when opening
  function handleOpen() {
    setTab('list')
    loadUsers()
  }

  if (!isOpen) return null

  // Trigger on first render of modal
  if (users === null && !listLoading) {
    handleOpen()
  }

  function handleCreated(user) {
    setUsers((prev) => [...(prev ?? []), user])
    onSelectUser(user)
    onClose()
  }

  function handleSaved(user) {
    setUsers((prev) => (prev ?? []).map((u) => (u.id === user.id ? user : u)))
    if (currentUser?.id === user.id) onSelectUser(user)
    setTab('list')
  }

  async function handleDelete(user) {
    if (!window.confirm(`Delete user "${user.username}"? This cannot be undone.`)) return
    await fetch(`${apiBase}/api/users/${user.id}`, { method: 'DELETE' })
    const next = (users ?? []).filter((u) => u.id !== user.id)
    setUsers(next)
    if (currentUser?.id === user.id) onSelectUser(null)
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal shell um-modal">
        {/* Header */}
        <div className="um-header">
          <div className="modal-tabs">
            <button
              type="button"
              className={`modal-tab ${tab === 'list' ? 'active' : ''}`}
              onClick={() => setTab('list')}
            >
              Switch User
            </button>
            <button
              type="button"
              className={`modal-tab ${tab === 'create' ? 'active' : ''}`}
              onClick={() => setTab('create')}
            >
              + New User
            </button>
            {tab === 'edit' && editTarget && (
              <button type="button" className="modal-tab active">
                Edit Profile
              </button>
            )}
          </div>
          <button type="button" className="um-close" onClick={onClose} aria-label="Close">×</button>
        </div>

        <div className="um-body panel-body scrollable">
          {/* ── User list ── */}
          {tab === 'list' && (
            <div className="um-list">
              {listLoading && <p className="muted">Loading users…</p>}
              {!listLoading && (users ?? []).length === 0 && (
                <p className="muted">No users yet. Create one to get started.</p>
              )}
              {(users ?? []).map((user) => (
                <div
                  key={user.id}
                  className={`um-user-card ${currentUser?.id === user.id ? 'active' : ''}`}
                >
                  <div className="um-user-avatar">
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                  <div className="um-user-details" onClick={() => { onSelectUser(user); onClose() }}>
                    <span className="um-username">{user.username}</span>
                    <div className="um-user-chips">
                      {(user.strengths ?? []).slice(0, 3).map((s) => (
                        <span key={s} className="um-chip strength">{s}</span>
                      ))}
                      {(user.weaknesses ?? []).slice(0, 3).map((w) => (
                        <span key={w} className="um-chip weakness">{w}</span>
                      ))}
                    </div>
                    <span className="um-stat">
                      {user.stats?.problems_solved ?? 0} problems solved
                    </span>
                  </div>
                  <div className="um-user-actions">
                    <button
                      type="button"
                      className="um-icon-btn"
                      onClick={() => { setEditTarget(user); setTab('edit') }}
                      title="Edit profile"
                    >
                      ✎
                    </button>
                    <button
                      type="button"
                      className="um-icon-btn danger"
                      onClick={() => handleDelete(user)}
                      title="Delete user"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Create ── */}
          {tab === 'create' && (
            <CreateView onCreated={handleCreated} apiBase={apiBase} />
          )}

          {/* ── Edit ── */}
          {tab === 'edit' && editTarget && (
            <EditView user={editTarget} apiBase={apiBase} onSaved={handleSaved} />
          )}
        </div>
      </div>
    </div>
  )
}
