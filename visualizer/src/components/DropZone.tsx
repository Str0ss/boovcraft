import { useEffect, useRef, useState } from 'react';
import { usePageState } from '../state/PageStateContext';
import styles from './DropZone.module.css';

export function DropZone() {
  const { dispatchers } = usePageState();
  const [visible, setVisible] = useState(false);
  const dragDepth = useRef(0);

  useEffect(() => {
    const onEnter = (e: DragEvent) => {
      if (!e.dataTransfer || !Array.from(e.dataTransfer.types).includes('Files')) return;
      e.preventDefault();
      dragDepth.current += 1;
      setVisible(true);
    };
    const onOver = (e: DragEvent) => {
      if (!e.dataTransfer || !Array.from(e.dataTransfer.types).includes('Files')) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'copy';
    };
    const onLeave = (e: DragEvent) => {
      if (!e.dataTransfer) return;
      dragDepth.current -= 1;
      if (dragDepth.current <= 0) {
        dragDepth.current = 0;
        setVisible(false);
      }
    };
    const onDrop = (e: DragEvent) => {
      if (!e.dataTransfer) return;
      e.preventDefault();
      dragDepth.current = 0;
      setVisible(false);
      const files = e.dataTransfer.files;
      if (!files || files.length !== 1) {
        dispatchers.loadFile(null);
        return;
      }
      const file = files[0];
      if (file) dispatchers.loadFile(file);
    };

    document.addEventListener('dragenter', onEnter);
    document.addEventListener('dragover', onOver);
    document.addEventListener('dragleave', onLeave);
    document.addEventListener('drop', onDrop);
    return () => {
      document.removeEventListener('dragenter', onEnter);
      document.removeEventListener('dragover', onOver);
      document.removeEventListener('dragleave', onLeave);
      document.removeEventListener('drop', onDrop);
    };
  }, [dispatchers]);

  if (!visible) return null;
  return (
    <div className={styles.dropzone}>
      <div className={styles.cue}>Drop to load</div>
    </div>
  );
}
