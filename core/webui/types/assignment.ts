import { Course } from "./course";
import { UserModel } from "./user";

export interface AssignmentStateWithAssignments {
  value: number;
  status: "idle" | "loading" | "error" | "completed";
  assignments: Assignment[];
}

export interface AssignmentStateWithUser {
  value: number;
  status: "idle" | "loading" | "error" | "completed";
  user: UserModel;
}

export interface Assignment {
  id: string;
  attributes: {
    status: "todo" | "in_progress" | "in_review" | "completed";
    course: {
      data: Course;
    };
    version: string;
    due_date: Date;
    start_date: Date;
    progress: number;
    comments: string;
  };
}
