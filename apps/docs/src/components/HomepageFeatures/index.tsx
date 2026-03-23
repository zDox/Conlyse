import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  Svg: React.ComponentType<React.ComponentProps<'svg'>>;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Powerful Replay System',
    Svg: require('@site/static/img/undraw_time-change.svg').default,
    description: (
      <>
        Record, compress, and replay full game timelines efficiently. ConflictInterface
        provides a bidirectional replay engine with fast time travel, support for multiple
        data type versions in a single replay, and a high-level API for navigating game state.
      </>
    ),
  },
  {
    title: 'End-to-End Replay Pipeline',
    Svg: require('@site/static/img/undraw_server-status.svg').default,
    description: (
      <>
        From Server Observer and Server Converter to storage backends, the project ships
        a full Docker-based deployment stack for ingesting game responses and persisting
        replay data reliably.
      </>
    ),
  },
  {
    title: 'Developer-Friendly Libraries',
    Svg: require('@site/static/img/undraw_open-source-code.svg').default,
    description: (
      <>
        Use the ConflictInterface Python library and replay interfaces directly in your
        own analysis tools. Clear APIs, strong abstractions, and detailed docs make it
        easy to build custom workflows around Conflict of Nations replays.
      </>
    ),
  },
];

function Feature({title, Svg, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <Svg className={styles.featureSvg} role="img" />
      </div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
