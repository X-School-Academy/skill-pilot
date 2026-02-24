import React, {useEffect, useState} from 'react';
// import { getSession } from 'next-auth/react';
import Head from 'next/head';
import { GetStaticPropsContext } from 'next';
import { serverSideTranslations } from 'next-i18next/serverSideTranslations'
import MarkdownRenderer from '../../components/blocks/MarkdownRenderer';


const EmbeddedVSCodeMarkdown = (props: any) => {

  const [code, setCode] = useState('');

  useEffect(() => {
    let notifier: any = null;

    if(!code){
      const storedCode = localStorage.getItem('jit-vscode-markdown') || '';
      setCode(storedCode);
    }

    const onMessage = async (event: any) => {
      const data = event.data;

      console.log('Received message from parent:', data);

      if (data === 'juniorit-vscode-md-reply') {
        if (notifier != null) {
          clearInterval(notifier);
          notifier = null;
        }
        return;
      }

      if (data.type === 'markdown' && data.content) {
        setCode(prevCode => {
          const newCode = data.content;
          setTimeout(() => {
            localStorage.setItem('jit-vscode-markdown', newCode);
          }, 0);
          return newCode;
        });
      }
    }

    window.addEventListener('message', onMessage);

    window.parent.postMessage('juniorit-embedded-vscode-md-page-ready', "*");

    notifier = setInterval(() => {
      window.parent.postMessage('juniorit-embedded-vscode-md-page-ready', "*");
    }, 1000)

      return () => {
        if (notifier != null) {
          clearInterval(notifier);
          notifier = null;
        }
        window.removeEventListener('message', onMessage);
      }

  }, [])

  return (
    <div className='w-full'>
      <Head>
        <title>Markdown Display</title>
      </Head>


      <div className="mx-auto px-3 pt-2">
        <div className='mx-auto mt-2'>

          <div className='prose max-w-none'>
            <MarkdownRenderer markdown={code} />
          </div>

        </div>
      </div>

  
      <style jsx>{`
        .error-message {
          color: red;
          font-size: 12px;
        }
        .result-message {
          color: green;
          font-size: 12px;
        }
      `}</style>
    </div>
  );
}

export const getStaticProps = async (context: GetStaticPropsContext) => {


  // let email = null
  // let jwt = null
  // if (session != null) {
  //   email = session?.user?.email
  //   jwt = session?.jwt
  // }
  // return {props:{email, jwt}}
  return {
    props: {
      // email, 
      // jwt, 
      ...(await serverSideTranslations(context.locale ?? 'en', [
        'common',
      ]))
    }
  }
};

export default EmbeddedVSCodeMarkdown;
