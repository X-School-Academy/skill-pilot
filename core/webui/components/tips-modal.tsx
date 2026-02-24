import React from "react";
import { Text, Button } from "@mantine/core";
import {
  ContextModalProps,
  OpenContextModal,
} from "@mantine/modals/lib/context";
import { modals } from "@mantine/modals";

export const showTipsModal = (message: string) => {
  const config: OpenContextModal<CustomModalProps> & {
    modal: string;
  } = {
    modal: "tipsModal",
    centered: true,
    withCloseButton: false,
    closeOnClickOutside: false,
    returnFocus: false,
    innerProps: {
      content: message,
    },
  };
  return modals.openContextModal(config);
};

export type CustomModalProps = {
  content: string;
  onConfirm?: () => void;
  confirmLabel?: string;
};

const TipsModal = ({
  context,
  id,
  innerProps,
}: ContextModalProps<CustomModalProps>) => (
  <>
    <Text size="md">{innerProps.content}</Text>
    <div className="flex justify-end">
      <Button
        mt="md"
        onClick={() => {
          // context.closeContextModal(id);
          modals.closeAll();
          innerProps.onConfirm?.call(null);
        }}
      >
        {innerProps.confirmLabel ?? "ok"}
      </Button>
    </div>
  </>
);

export default TipsModal;
