// Time/date formatting helpers for dashboard
export function formatLocal(isoValue) {
  if(!isoValue) return ''
  try {
    const d = new Date(isoValue)
    if(isNaN(d.getTime())) return isoValue
    return d.toLocaleString(undefined, {
      year: 'numeric', month: 'short', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    })
  } catch { return isoValue }
}

export function formatLocalShort(isoValue){
  if(!isoValue) return ''
  try {
    const d = new Date(isoValue)
    if(isNaN(d.getTime())) return isoValue
    return d.toLocaleString(undefined, { month:'short', day:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' })
  } catch { return isoValue }
}

// Backwards-compatible aliases (earlier code referenced IST helpers; we now treat locale local time)
export function formatIST(isoValue){
  return formatLocal(isoValue)
}

export function formatISTShort(isoValue){
  return formatLocalShort(isoValue)
}
