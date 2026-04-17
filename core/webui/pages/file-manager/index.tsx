import Head from 'next/head';
import dynamic from 'next/dynamic';

const FileManagerContent = dynamic(
  () => import('../../components/FileManagerContent'),
  { ssr: false, loading: () => (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: '#868e96', fontSize: 14 }}>
      Loading file manager…
    </div>
  )},
);

export default function FileManagerPage() {
  return (
    <>
      <Head>
        <title>File Manager — Skill Pilot</title>
      </Head>
      <main style={{ height: '100vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <FileManagerContent />
      </main>
    </>
  );
}
