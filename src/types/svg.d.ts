declare module '*.svg' {
  import * as React from 'react';

  // Named export for React component
  export const ReactComponent: React.FunctionComponent;
  React.SVGProps<SVGSVGElement> & { title: string };

  // Default export for URL
  const src: string;
  export default src;
}

// 또는 ?react suffix를 위한 타입 정의
declare module '*.svg?react' {
  import * as React from 'react';
  const ReactComponent: React.FunctionComponent<React.SVGProps<SVGSVGElement>>;
  export default ReactComponent;
}
