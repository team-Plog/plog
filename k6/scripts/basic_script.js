import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
    stages: [
        {
            duration: '1m',
            target: 1000
        }
    ]
};

export default function () {
    http.get('http://spring-mock-service:8080/api/basic');
    sleep(1);
}