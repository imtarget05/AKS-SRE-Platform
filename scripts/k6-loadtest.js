import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 20 },  // Ramp-up to 20 VUs
    { duration: '30s', target: 20 },  // Hold 20 VUs
    { duration: '5s', target: 0 },    // Ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'], // 95% of requests must complete below 500ms
    http_req_failed: ['rate<0.01'],                 // Error rate < 1%
  },
};

const BASE_URL = 'https://portfolio-api-edge.tanmainguyenbinh.workers.dev';

export default function () {
  // 1. Health check probe
  const healthRes = http.get(`${BASE_URL}/flashsale/health/live`);
  check(healthRes, {
    'health status is 200': (r) => r.status === 200,
    'health response is healthy': (r) => r.body.includes('healthy'),
  });

  // 2. Read product endpoint
  const productRes = http.get(`${BASE_URL}/flashsale/api/products/1`);
  check(productRes, {
    'product status is 200': (r) => r.status === 200,
    'product response has id 1': (r) => r.body.includes('"id":1'),
  });

  sleep(0.1);
}
