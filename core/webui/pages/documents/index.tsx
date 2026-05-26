import dynamic from 'next/dynamic';
import MainLayout from '../../components/main-layout';

const FileManagerContent = dynamic(
  () => import('../../components/FileManagerContent'),
  { ssr: false, loading: () => (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#868e96', fontSize: 14 }}>
      Loading documents...
    </div>
  )},
);

export default function DocumentsPage() {
  return (
    <MainLayout title="Documents">
      <main style={{ height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <FileManagerContent
          title="Documents"
          scopedRootPath="/workspace/documents"
          hideDirectoryTree
          hideStandaloneHeader
          routePathname="/documents"
        />
      </main>
    </MainLayout>
  );
}
