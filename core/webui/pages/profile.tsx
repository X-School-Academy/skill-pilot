import { GetStaticPropsContext } from 'next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations';

import HomePage from './index';

export default function ProfilePage() {
  return <HomePage initialView="profile" />;
}

export const getStaticProps = async (context: GetStaticPropsContext) => ({
  props: {
    ...(await serverSideTranslations(context.locale ?? 'en', ['common'])),
  },
});
