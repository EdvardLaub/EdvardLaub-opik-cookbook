// Next.js calls register() once at server start. The OTel setup needs Node APIs,
// so it only loads in the Node.js runtime (Next also compiles this file for Edge).
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./instrumentation.node");
  }
}
