/* Mist live background (DESIGN.md §6.3), taken from design/reference-shaders.js.
   Mist only, no chrome. Kept light because this machine's GPU is for models:
   half resolution, 24 fps cap, paused when the window is hidden or minimised.
   Reduced motion: one still frame. */
(() => {
  const canvas = document.querySelector('[data-mist]');
  if (!canvas) return;
  const gl = canvas.getContext('webgl2', { antialias: false, alpha: false, depth: false, powerPreference: 'low-power' });
  if (!gl) { canvas.remove(); return; }

  const vert = `#version 300 es
  void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
  }`;
  const frag = `#version 300 es
  precision highp float;
  out vec4 fragColor;
  uniform vec2 uRes; uniform float uTime; uniform float uMist;
  float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
  }
  float fbm(vec2 p) {
    float v = 0.0, a = 0.5; mat2 m = mat2(1.6, 1.2, -1.2, 1.6);
    for (int i = 0; i < 5; i++) { v += a * noise(p); p = m * p; a *= 0.5; }
    return v;
  }
  float mist(vec2 uv, float t) {
    float c = cos(-0.8727), s = sin(-0.8727);
    uv = mat2(c, -s, s, c) * uv * 1.15;
    vec2 q = vec2(fbm(uv + vec2(0.0, t * 0.035)), fbm(uv + vec2(5.2, 1.3) - t * 0.03));
    vec2 r = vec2(fbm(uv + 2.6 * q + vec2(1.7, 9.2) + t * 0.022), fbm(uv + 2.6 * q + vec2(8.3, 2.8) - t * 0.018));
    float f = fbm(uv + 2.4 * r);
    float ridge = smoothstep(0.42, 0.72, f) * (1.0 - smoothstep(0.78, 1.0, f));
    return pow(ridge, 1.35) * (0.55 + 0.45 * clamp(length(r), 0.0, 1.0));
  }
  vec3 aces(vec3 x) { return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }
  void main() {
    vec2 uv = (gl_FragCoord.xy * 2.0 - uRes) / uRes.y;
    float col = mist(uv * 0.9, uTime) * uMist;
    vec3 c3 = pow(aces(vec3(col) * 1.1), vec3(1.0 / 2.2));
    c3 = min(c3, vec3(0.93));
    c3 += (hash(gl_FragCoord.xy + fract(uTime) * 91.0) - 0.5) * 0.045;
    fragColor = vec4(c3, 1.0);
  }`;

  const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; };
  const prog = gl.createProgram();
  gl.attachShader(prog, sh(gl.VERTEX_SHADER, vert));
  gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, frag));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { canvas.remove(); return; }
  gl.useProgram(prog);
  const uRes = gl.getUniformLocation(prog, 'uRes');
  const uTime = gl.getUniformLocation(prog, 'uTime');
  const uMist = gl.getUniformLocation(prog, 'uMist');
  gl.bindVertexArray(gl.createVertexArray());

  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const SCALE = 0.5, FPS = 24;
  let brightness = 0.36, target = 0.36;   // hero-underlay strength (§6.3)
  const t0 = performance.now();
  let last = 0, raf = 0;

  function resize() {
    const w = Math.max(1, Math.round(innerWidth * SCALE)), h = Math.max(1, Math.round(innerHeight * SCALE));
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    gl.viewport(0, 0, w, h);
    gl.uniform2f(uRes, w, h);
  }
  function draw(now) {
    brightness += (target - brightness) * 0.06;
    gl.uniform1f(uTime, (now - t0) / 1000 * 0.9 + 40);
    gl.uniform1f(uMist, brightness);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  function loop(now) {
    raf = requestAnimationFrame(loop);
    if (now - last < 1000 / FPS) return;
    last = now;
    draw(now);
  }
  function start() { if (!raf && !reduced) raf = requestAnimationFrame(loop); }
  function stop() { cancelAnimationFrame(raf); raf = 0; }

  resize();
  draw(performance.now());
  canvas.classList.add('is-on');
  addEventListener('resize', () => { resize(); if (reduced) draw(performance.now()); });
  document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
  start();

  // Views set the strength: brighter on the home screen, dimmer behind dense tables.
  window.DPMist = { level(v) { target = v; if (reduced) { brightness = v; draw(performance.now()); } } };
})();
