/* GLSL for the two live backgrounds.
   - Mist (design.md §6.3): domain-warped fbm smoke, black / white / black, rotated -50°.
   - Liquid chrome (AnimatedWebs "Liquid Chrome Audio" hero): six smooth-union spheres,
     reflection-only shading of a procedural studio. Recoloured to pure monochrome:
     no RGB dispersion, no warm/cool strips, a horizontal brushed grain on the metal,
     and the miss rays show Mist instead of the studio. */
window.DARK_SHADERS = (() => {
  const vert = `#version 300 es
  void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
  }`;

  const frag = `#version 300 es
  precision highp float;
  out vec4 fragColor;

  uniform vec2  uRes;
  uniform float uTime;
  uniform vec4  uS[6];      // xyz centre, w radius
  uniform vec3  uMouse;     // xy world position, z ripple strength
  uniform float uKick;      // click splash, decays to 0
  uniform int   uSteps;
  uniform float uBlobs;     // 1 = chrome hero, 0 = mist only
  uniform float uMist;      // mist brightness

  float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x),
               mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
  }
  float fbm(vec2 p) {
    float v = 0.0, a = 0.5;
    mat2 m = mat2(1.6, 1.2, -1.2, 1.6);
    for (int i = 0; i < 5; i++) { v += a * noise(p); p = m * p; a *= 0.5; }
    return v;
  }

  // ── Mist ────────────────────────────────────────────────────────────────
  float mist(vec2 uv, float t) {
    float c = cos(-0.8727), s = sin(-0.8727);           // -50°
    uv = mat2(c, -s, s, c) * uv * 1.15;
    vec2 q = vec2(fbm(uv + vec2(0.0, t * 0.035)), fbm(uv + vec2(5.2, 1.3) - t * 0.03));
    vec2 r = vec2(fbm(uv + 2.6 * q + vec2(1.7, 9.2) + t * 0.022),
                  fbm(uv + 2.6 * q + vec2(8.3, 2.8) - t * 0.018));
    float f = fbm(uv + 2.4 * r);
    // black → white → black: bright only on the ridge of the field
    float ridge = smoothstep(0.42, 0.72, f) * (1.0 - smoothstep(0.78, 1.0, f));
    return pow(ridge, 1.35) * (0.55 + 0.45 * clamp(length(r), 0.0, 1.0));
  }

  // ── Chrome SDF ──────────────────────────────────────────────────────────
  float smin(float a, float b, float k) {
    float h = max(k - abs(a - b), 0.0) / k;
    return min(a, b) - h * h * k * 0.25;
  }
  float map(vec3 p) {
    float d = 1e5;
    for (int i = 0; i < 6; i++) d = smin(d, length(p - uS[i].xyz) - uS[i].w, 0.85);
    d += 0.025 * sin(p.x * 3.1 + uTime * 1.3) * sin(p.y * 2.7 - uTime * 1.1) * sin(p.z * 2.3 + uTime * 0.9);
    float md = length(p.xy - uMouse.xy);
    d += uMouse.z * 0.035 * sin(md * 9.0 - uTime * 6.0) * exp(-md * 1.6);
    d += uKick * 0.05 * sin(length(p) * 8.0 - uTime * 10.0);
    return d;
  }
  vec3 normal(vec3 p) {
    const vec2 k = vec2(1, -1) * 0.0015;
    return normalize(k.xyy * map(p + k.xyy) + k.yyx * map(p + k.yyx) +
                     k.yxy * map(p + k.yxy) + k.xxx * map(p + k.xxx));
  }

  // Monochrome studio: black room, overhead softbox, a window grid of hard
  // white softboxes, thin strip lights and a striped glossy floor.
  float env(vec3 r) {
    float y = r.y;
    float c = 0.012;
    c += 1.5 * smoothstep(0.80, 0.90, y);                                     // overhead
    float a = atan(r.x, -r.z);
    float win = step(0.55, sin(a * 7.0)) * step(0.55, sin(y * 18.0 + 1.0));
    c += 1.15 * win * smoothstep(0.02, 0.10, y) * (1.0 - smoothstep(0.42, 0.50, y));
    c += 0.85 * exp(-pow((y - 0.24) * 46.0, 2.0));                            // sharp horizon line
    c += 0.55 * smoothstep(0.93, 0.99, abs(r.x)) * smoothstep(-0.1, 0.3, y);  // side strips
    if (y < 0.0) {
      // soft glossy floor stripes, faded out before the horizon where they would alias
      float stripe = 0.5 + 0.5 * sin(r.x / (0.25 - y) * 9.0);
      c = 0.015 + 0.08 * stripe * smoothstep(-0.9, -0.35, y) * (1.0 - smoothstep(-0.12, -0.02, y))
            + 0.22 * exp(y * 22.0);
    }
    return c;
  }

  vec3 aces(vec3 x) { return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }

  void main() {
    vec2 uv = (gl_FragCoord.xy * 2.0 - uRes) / uRes.y;
    float m = mist(uv * 0.9, uTime);
    float col = m * uMist;

    if (uBlobs > 0.5) {
      vec3 ro = vec3(0.0, 0.0, 6.2);
      vec3 rd = normalize(vec3(uv, -1.75));
      float t = 0.0, minD = 1e5, d = 1e5;
      bool hit = false, far = false;
      for (int i = 0; i < 64; i++) {
        if (i >= uSteps) break;
        vec3 p = ro + rd * t;
        d = map(p);
        minD = min(minD, d);
        if (d < 0.0015) { hit = true; break; }
        t += d * 0.9;
        if (t > 14.0) { far = true; break; }
      }
      // ran out of steps while grazing the surface: count it as a hit (no edge speckles)
      if (!hit && !far && d < 0.06) hit = true;
      if (hit) {
        vec3 p = ro + rd * t;
        vec3 n = normal(p);
        // brushed grain: horizontal micro-scratches perturb the normal along y
        float g = noise(vec2(p.x * 2.0, p.y * 70.0)) - 0.5;
        n = normalize(n + vec3(0.0, g * 0.022, 0.0));
        vec3 r = reflect(rd, n);
        float c = env(r);
        float fres = pow(1.0 - max(dot(-rd, n), 0.0), 5.0);
        c *= mix(0.62, 1.15, fres);
        float ao = clamp(map(p + n * 0.4) / 0.4, 0.0, 1.0);
        c *= 0.45 + 0.55 * ao;
        col = c;
      } else {
        col = col * 0.75 + exp(-minD * 4.0) * 0.06;
      }
    }

    vec3 c3 = aces(vec3(col) * 1.1);
    c3 = pow(c3, vec3(1.0 / 2.2));
    c3 = min(c3, vec3(0.93));                                               // top out near #DCDCDC
    c3 += (hash(gl_FragCoord.xy + fract(uTime) * 91.0) - 0.5) * 0.045;       // grain, ~0.2
    fragColor = vec4(c3, 1.0);
  }`;

  return { vert, frag };
})();
