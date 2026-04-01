import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';
import OpenSourceCodeSvg from '@site/static/img/undraw_open-source-code.svg';
import TimeChangeSvg from '@site/static/img/undraw_time-change.svg';
import ServerStatusSvg from '@site/static/img/undraw_server-status.svg';


type FeatureItem = {
  title: string;
  Svg: React.ComponentType<React.ComponentProps<'svg'>>;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Powerful Replay System',
    Svg: TimeChangeSvg,
    description: (
      <>
        ConflictInterface delivers bidirectional time travel across game history with
        compact patch-based storage. Jump, rewind, and fast-forward through state changes
        efficiently while preserving accurate replay semantics.
      </>
    ),
  },
  {
    title: 'End-to-End Replay Pipeline',
    Svg: ServerStatusSvg,
    description: (
      <>
        From Server Observer and Server Converter to storage backends, the project ships
        a full Docker-based deployment stack for ingesting game responses and persisting
        replay data reliably.
      </>
    ),
  },
  {
    title: 'Desktop Client',
    Svg: OpenSourceCodeSvg,
    description: (
      <>
        Conlyse provides a high-performance desktop experience with OpenGL-powered map
        rendering, precision playback controls and dockable panels. Analyze
        replays with multiple map views and a modern themed interface.
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
