import React from "react";
import { Role, User, UserModel } from "./user";

export interface OnlineCourseSessionEntity {
  id: number;
  attributes: OnlineCourseSession;
}

export interface OnlineCourseSession {
  session_id: string;
  course_name: string;
  holder:
    | {
        data: {
          attributes: User;
        } | null;
      }
    | null
    | undefined;
  max_limit_student: number;
  max_limit_teacher: number;
  task1: OnlineCourseTask | undefined;
  task2: OnlineCourseTask | undefined;
  task3: OnlineCourseTask | undefined;
  progress: number;
}

export interface OnlineCourseInfo {
  id: string;
  role: Role;
  auth: string;
  course_data: string | OnlineCourseTask[]; // Json string in db, OnlineCourseTaskItem[] in client side
  session:
    | {
        data: {
          id: string;
          attributes: OnlineCourseSession;
        };
      }
    | ({ id: number } & OnlineCourseSession)
    | null;
  level: CourseLevelEntity | undefined;
}

export enum CourseState {
  idle,
  connecting,
  success,
  fail,
  sending,
}

export interface ConnectStateHandler {
  onConnected: () => void;
  onReconnect?: () => void;
  onConnectError?: (error: any) => void;
}

export interface SocketMessageHandler {
  onCount?: MessageCallback;
  onAssignTask?: MessageCallback;
  onWrongRoom?: MessageCallback;
  onRoomUserChange?: MessageCallback;
  onStudentCodeInput?: MessageCallback;
  onStudentResultOutput?: MessageCallback;
  onStudentTaskStatusChanged?: MessageCallback;
  onCourseModeChanged?: MessageCallback;
}

export interface OnlineCourseEventCallback {
  taskId?: number | string;
  onlineCourseSessionId?: string;
  onDocChanged?: (input: string | undefined) => void;
  onSubmit?: () => void;
  onError?: () => void;
  onReset?: () => void;
}

export type MessageCallback = (message: any) => void;

export type VisibleTaskChangedCallback = (
  isIntersecting: boolean,
  task: OnlineCourseTaskEntity
) => void;

export interface TaskChangedState {
  codeInput: string | undefined;
  resultOutput: string | undefined;
}

export type TaskId = number | string;

// <Key: taskId, value: TaskChangedState>
export type StudentTaskChangedState = Map<TaskId, TaskChangedState>;

export interface TaskStatusObject {
  taskId: TaskId;
  status: TaskStatus;
  count: number;
}

// <Key: studentId, value: Record<TaskStatus, number>[]>
export type StudentTaskStatusMap = Map<number | string, TaskStatusObject[]>;

export const StudentInputContext = React.createContext<
  StudentTaskChangedState | undefined
>(undefined);

export enum MessageType {
  count = "count",
  sendTask = "sendTask",
  assignTask = "assignTask",
  wrongInfo = "wrongInformation",
  roomUserChange = "roomUserChange",
  studentCodeInput = "studentCodeInput",
  studentResultOutput = "studentResultOutput",
  studentTaskStatusChanged = "studentTaskStatusChanged",
  courseModeChange = "courseModeChange",
}

export interface Message {
  type: MessageType;
  data: any;
}

export interface CourseLevelEntity {
  id: number;
  attributes: CourseLevel;
}
export interface CourseLevel {
  name: string;
  description: string;
}


export type CourseMode = "Real-time" | "Follow Video";

export type TaskStatus = "updated" | "completed" | "error";

export interface OnlineCourseTaskEntity {
  id: number;
  attributes: OnlineCourseTask;
}
export interface OnlineCourseTask {
  index: number;
  teacher?: {
    data: UserModel;
  } | null;
  task: string; //frontend/pages/online-course/teacher/[id].tsx line 137
  code: string | null; //api-server/app/online-course/course.ts line 42
  result: string | null; //api-server/app/online-course/course.ts line 43
  time: string;
  session?: {
    data: OnlineCourseSessionEntity;
  } | null;
  level: CourseLevel | null;
  student?: {
    data: UserModel;
  } | null;
  status?: TaskStatus | null;
  mode: CourseMode;
}
export interface SessionStudentTaskMapper {
  id: number;
  attributes: {
    session: {
      data: {
        id: number;
        attributes: OnlineCourseSession;
      };
    };
    student: UserModel;
    task: {
      data: OnlineCourseTaskEntity;
    };
  };
}
