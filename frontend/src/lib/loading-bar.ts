type Listener = (loading: boolean) => void;

let activeRequests = 0;
const listeners = new Set<Listener>();

function notify() {
  const loading = activeRequests > 0;
  listeners.forEach((fn) => fn(loading));
}

export function startLoading() {
  activeRequests++;
  notify();
}

export function stopLoading() {
  activeRequests = Math.max(0, activeRequests - 1);
  notify();
}

export function subscribe(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function isLoading(): boolean {
  return activeRequests > 0;
}
