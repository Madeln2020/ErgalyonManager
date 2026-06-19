// ═══════════════════════════════════════════════════════════════════
// EDM v2 — k6 Load Test Script
//
// Run:
//   k6 run load-tests/k6/scenario.js
//
// Options:
//   k6 run --vus 10 --duration 30s load-tests/k6/scenario.js
// ═══════════════════════════════════════════════════════════════════

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ── Custom metrics ─────────────────────────────────────────────────
const errorRate = new Rate('errors');
const supplierLatency = new Trend('suppliers_latency');
const productLatency = new Trend('products_latency');
const healthLatency = new Trend('health_latency');

// ── Configuration ──────────────────────────────────────────────────
export const options = {
  stages: [
    { duration: '10s', target: 5 },   // Ramp up to 5 VUs
    { duration: '20s', target: 10 },  // Ramp to 10 VUs
    { duration: '10s', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests under 2s
    errors: ['rate<0.1'],              // Error rate < 10%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8887';

// ── Test scenarios ─────────────────────────────────────────────────
export default function () {
  group('Health Check', () => {
    const res = http.get(`${BASE_URL}/health`);
    healthLatency.add(res.timings.duration);
    const ok = check(res, {
      'health status is 200': (r) => r.status === 200,
      'health returns ok': (r) => r.json('status') === 'ok',
    });
    errorRate.add(!ok);
    sleep(1);
  });

  group('Suppliers', () => {
    const res = http.get(`${BASE_URL}/api/v1/suppliers`);
    supplierLatency.add(res.timings.duration);
    const ok = check(res, {
      'suppliers status is 200': (r) => r.status === 200,
      'suppliers returns list': (r) => Array.isArray(r.json()),
    });
    errorRate.add(!ok);
    sleep(0.5);
  });

  group('Products (paginated)', () => {
    // Test pagination at different offsets
    for (let offset = 0; offset < 20; offset += 10) {
      const res = http.get(`${BASE_URL}/api/v1/products?limit=10&offset=${offset}`);
      productLatency.add(res.timings.duration);
      const ok = check(res, {
        'products status is 200': (r) => r.status === 200,
        'products returns items': (r) => r.json('items') !== undefined,
        'products has total': (r) => r.json('total') !== undefined,
      });
      errorRate.add(!ok);
      sleep(0.3);
    }
  });

  group('Review Queue', () => {
    const res = http.get(`${BASE_URL}/api/v1/review-queue?status=open&limit=10`);
    const ok = check(res, {
      'review status is 200': (r) => r.status === 200,
      'review returns items': (r) => r.json('items') !== undefined,
    });
    errorRate.add(!ok);
    sleep(0.5);
  });

  group('Product Search', () => {
    const res = http.get(`${BASE_URL}/api/v1/products?search=test&limit=5`);
    const ok = check(res, {
      'search status is 200': (r) => r.status === 200,
    });
    errorRate.add(!ok);
    sleep(0.5);
  });

  // Rate limiter test — hit an endpoint rapidly
  group('Rate Limiting', () => {
    let limited = false;
    for (let i = 0; i < 12; i++) {
      const res = http.get(`${BASE_URL}/api/v1/suppliers`);
      if (res.status === 429) {
        limited = true;
        break;
      }
    }
    check(limited, {
      'rate limiter eventually blocks': (v) => v === true,
    });
  });
}
