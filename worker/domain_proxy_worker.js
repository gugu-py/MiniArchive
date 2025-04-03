export default {
  async fetch(request, env, ctx) {
    // The target Cloud Run URL
    const targetUrl = "https://your-cloud-run-domain";

    // Construct the new URL by appending the requested path and query
    const url = new URL(request.url);
    const target = new URL(targetUrl);
    target.pathname = url.pathname;
    target.search = url.search;

    // Create a request object with the original headers, pointing to the new target URL
    const proxyRequest = new Request(target.toString(), request);

    // Fetch the response from the Cloud Run service
    const response = await fetch(proxyRequest);

    // Return the response, passing through the headers and status from Cloud Run
    return new Response(response.body, response);
  },
};
