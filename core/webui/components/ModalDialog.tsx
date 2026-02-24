import React, { useState, useRef, useEffect, PropsWithChildren } from 'react';

interface Props {
  title: string;
  isOpen: boolean;
  toolbar?: boolean;
  width?: number;
  height?: number;
  showCancel?: boolean;
  isModal?: boolean;
  onClose?: () => void;
  onConfirm?: () => void;
}

const ModalDialog: React.FC<PropsWithChildren<Props>> = ({ title, children, width, height, isOpen, toolbar, showCancel, isModal, onClose, onConfirm }) => {
  const [visibility, setVisibility] = useState(isOpen);
  const modalRef = useRef<HTMLDivElement>(null);

  const handleClose = () => {
    setVisibility(false);
    if (onClose) onClose();
  };

  const handleConfirm = () => {
    setVisibility(false);
    if (onConfirm) onConfirm();
    if (onClose) onClose();
  };

  const handleClickOutside = (event: MouseEvent) => {
    if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
      if (!(isModal ?? true)) {
        setVisibility(false);
        if (onClose) onClose();
      }
    }
  };

  useEffect(() => {
    if (visibility) {
      document.addEventListener('mousedown', handleClickOutside);
    } else {
      document.removeEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [visibility]);

  useEffect(() => {
    setVisibility(isOpen);
  }, [isOpen]);

  return (
    <div style={{ display: visibility ? 'flex' : 'none', justifyContent: 'center', alignItems: 'center', position: 'fixed', zIndex: 100000, top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div ref={modalRef} className="modal-dialog" style={{ backgroundColor: 'white', borderRadius: '10px', padding: '0 20px 20px 20px', height: height ?? 'auto', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid lightgray', paddingBottom: '0px', marginBottom: '10px' }}>
          <h2 style={{ margin: 0 }}><b>{title}</b></h2>
          <button onClick={handleClose} style={{ backgroundColor: 'transparent', border: 'none', cursor: 'pointer' }}>
            <span style={{ fontSize: '36px', color: 'black' }}>&times;</span>
          </button>
        </div>
        <div>
          {children}
        </div>
        {(toolbar === undefined || toolbar) &&
          <div style={{ borderTop: '0px solid lightgray', paddingTop: '10px', marginTop: '10px', display: 'flex', justifyContent: 'flex-end' }}>
            {showCancel ? <button onClick={handleClose} className="w-28 rounded h-10 bg-white border border-gray-300 text-gray-900 font-medium ml-6">
              Cancel
            </button> : null}
            <button onClick={handleConfirm} className="w-28 rounded h-10 border-primary-blue text-white font-medium bg-primary-blue ml-6">
              OK
            </button>
          </div>
        }
      </div>
      <style jsx>{`
      .modal-dialog {
        width: 90vw;
      }
      @media only screen and (min-width: 600px) {
        .modal-dialog {
          max-width: ${width ?? '890'}px;
        }
      }
      `}</style>
    </div>
  );
};

export default ModalDialog;
