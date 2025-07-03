import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
    scenarios: {
        scenario: {
            executor: 'ramping-vus',
            stages: [
                { duration: '100s', target: 1000 },
            ],
            exec: 'scenario',
        },
    }
};

export function scenario() {
    http.get('http://spring-mock-service:8080/api/io/sleep/500');
    sleep(1.0);
}
