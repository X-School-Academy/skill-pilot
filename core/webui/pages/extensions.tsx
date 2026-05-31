import { GetStaticPropsContext } from 'next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import HomePage from './index';

export default function ExtensionsPage() {
  return <HomePage initialView="extensions" />;
}

export const getStaticProps = async (context: GetStaticPropsContext) => ({
  props: {
    ...(await serverSideTranslations(context.locale ?? 'en', ['common'])),
  },
});
