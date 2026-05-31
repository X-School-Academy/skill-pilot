import { GetStaticPropsContext } from 'next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import HomePage from './index';

export default function McpServersPage() {
  return <HomePage initialView="mcp-servers" />;
}

export const getStaticProps = async (context: GetStaticPropsContext) => ({
  props: {
    ...(await serverSideTranslations(context.locale ?? 'en', ['common'])),
  },
});
