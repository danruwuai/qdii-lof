export async function onRequest(context) {
  const { request, env } = context;
  const response = await env.api.fetch(request);
  return response;
}
