const api = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function forward(request: Request, { params }: { params: Promise<{ action: string[] }> }) {
  const { action } = await params;
  if (action.length !== 1 || !/^(register|login|logout|forgot|reset|me|password|collections|admin|assistant|conversations|preferences|searches|recommendations)$/.test(action[0])) {
    return Response.json({ detail: 'Account route not found' }, { status: 404 });
  }

  const headers = new Headers();
  for (const name of ['origin', 'cookie', 'content-type']) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  try {
    const upstreamPath = '/api/auth/' + action[0] + new URL(request.url).search;
    const upstream = await fetch(new URL(upstreamPath, api), {
      method: request.method,
      headers,
      body: request.method === 'GET' ? undefined : await request.text(),
      redirect: 'manual',
      cache: 'no-store',
      signal: AbortSignal.timeout(action[0] === 'assistant' ? 80000 : 12000),
    });
    const responseHeaders = new Headers({ 'Cache-Control': 'no-store, no-transform' });
    for (const name of ['content-type', 'retry-after', 'x-accel-buffering']) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    for (const cookie of upstream.headers.getSetCookie()) responseHeaders.append('set-cookie', cookie);
    return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch {
    return Response.json({ detail: 'Account service is temporarily unavailable' }, { status: 503 });
  }
}

export { forward as GET, forward as POST, forward as PATCH, forward as DELETE };
