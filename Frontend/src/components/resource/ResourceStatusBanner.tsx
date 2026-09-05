import './resource.css'

interface Props {
  status: 'idle' | 'loading' | 'ready' | 'partial' | 'error'
  errorMessage?: string | null
  warnings?: string[]
}

export function ResourceStatusBanner({ status, errorMessage, warnings }: Props) {
  if (status === 'loading') {
    return (
      <div className="status-banner loading">
        <span className="spinner" />
        <span>
          Fetching the transcript and building the index — this can take a little while for
          longer videos or playlists.
        </span>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="status-banner error">
        <span>⚠️</span>
        <span>{errorMessage || 'Something went wrong analyzing that resource.'}</span>
      </div>
    )
  }

  if (status === 'partial') {
    return (
      <div className="status-banner partial">
        <div>
          <strong>Ready, with some gaps.</strong> A few videos couldn't be indexed:
          {warnings && warnings.length > 0 && (
            <ul>
              {warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    )
  }

  return null
}
