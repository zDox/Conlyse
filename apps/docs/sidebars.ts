import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */
const sidebars: SidebarsConfig = {
  tutorialSidebar: [
    'intro',
    {
      type: 'category',
      label: 'User Guide',
      items: ['user-guide/deployment'],
    },
    {
      type: 'category',
      label: 'Developer Guide',
      items: [
        {
          type: 'category',
          label: 'Services',
          items: [
            'developer-guide/services/server-observer',
            'developer-guide/services/server-converter',
          ],
        },
        {
          type: 'category',
          label: 'Libraries',
          items: [
            {
              type: 'category',
              label: 'ConflictInterface',
              items: [
                'developer-guide/libraries/conflict-interface/replay-system',
              ],
            },
          ],
        },
      ],
    },
  ],
};

export default sidebars;
