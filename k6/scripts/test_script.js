import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
    scenarios: {
        scenario1: {
            executor: 'ramping-vus',
            stages: [
                { duration: '100s', target: 1000 },
                { duration: '10s', target: 2000}
            ],
            exec: 'scenario1',
        },
        scenario2: {
            executor: 'constant-vus',
            vus: 100,
            duration: '100s',
            exec: 'scenario2'
        }
    }
};

export function scenario1() {
    http.get('http://spring-mock-service:8080/api/io/sleep/500');
    sleep(1.0);
}

export function scenario2(){
    http.get('http://spring-mock-service:8080/api/basic');
    sleep(1.0);
}
