import { NextRequest, NextResponse } from 'next/server';

const HEROKU_BACKEND = 'https://publishing-command-center-d6e1f2c72672.herokuapp.com';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

async function handleProxy(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = (params.path || []).join('/');
  const search = req.nextUrl.search || '';
  const targetUrl = `${HEROKU_BACKEND}/api/${path}${search}`;

  const headers = new Headers();
  req.headers.forEach((val, key) => {
    const k = key.toLowerCase();
    if (k !== 'host' && k !== 'origin' && k !== 'referer' && k !== 'connection') {
      headers.set(key, val);
    }
  });

  const method = req.method;
  const options: RequestInit = {
    method,
    headers,
    cache: 'no-store',
  };

  if (method !== 'GET' && method !== 'HEAD') {
    options.body = await req.arrayBuffer();
  }

  try {
    const backendRes = await fetch(targetUrl, options);
    const resHeaders = new Headers();
    backendRes.headers.forEach((val, key) => {
      const k = key.toLowerCase();
      if (k !== 'content-encoding' && k !== 'transfer-encoding') {
        resHeaders.set(key, val);
      }
    });

    const bodyBuffer = await backendRes.arrayBuffer();
    return new NextResponse(bodyBuffer, {
      status: backendRes.status,
      statusText: backendRes.statusText,
      headers: resHeaders,
    });
  } catch (err: any) {
    return NextResponse.json({ error: `Backend proxy error: ${err.message}` }, { status: 502 });
  }
}

export const GET = handleProxy;
export const POST = handleProxy;
export const PUT = handleProxy;
export const DELETE = handleProxy;
export const PATCH = handleProxy;
export const HEAD = handleProxy;
export const OPTIONS = handleProxy;
