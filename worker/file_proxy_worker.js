export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    if (pathname === "/generate-link") {
      // Handle link generation
      return await handleGenerateLink(request, env);
    } else if (pathname.startsWith("/tmp/") && pathname.endsWith(".pdf")) {
      // Handle accessing the temporary link
      const tmpKey = pathname.slice(5, -4); // Extract key after '/tmp/' and remove '.pdf'
      return await handleProxyLink(tmpKey, env);
    } else {
      return new Response("Invalid endpoint", { status: 404 });
    }
  },
};

async function handleGenerateLink(request, env) {
  const url = new URL(request.url);
  const signedUrl = url.searchParams.get("signedUrl");
  const expireSeconds = parseInt(url.searchParams.get("expireSeconds"));

  if (!signedUrl || isNaN(expireSeconds)) {
    return new Response("Missing signedUrl or expireSeconds", { status: 400 });
  }

  // Generate a unique key
  const tmpKey = crypto.randomUUID();
  const tmpPath = `/tmp/${tmpKey}.pdf`;

  // Construct the full URL using the request's host
  const baseUrl = `${url.protocol}//${url.host}`;
  const tmpLink = `${baseUrl}${tmpPath}`;

  // Store the signed URL in KV with expiration
  await env.TEMP_LINKS.put(tmpKey, signedUrl, { expirationTtl: expireSeconds });

  return new Response(JSON.stringify({ tmpLink }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

async function handleProxyLink(tmpKey, env) {
  // Retrieve the signed URL from KV
  const signedUrl = await env.TEMP_LINKS.get(tmpKey);

  if (!signedUrl) {
    return new Response("Temporary link expired or invalid", { status: 404 });
  }

  // Proxy the signed URL
  const response = await fetch(signedUrl);
  const headers = new Headers(response.headers);

  // Ensure the Content-Disposition header forces a PDF filename
  headers.set("Content-Disposition", 'inline; filename="file.pdf"');

  return new Response(response.body, {
    status: response.status,
    headers,
  });
}
