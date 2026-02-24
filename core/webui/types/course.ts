import { Assignment } from "./assignment";

export interface Course {
  id: string;
  attributes: {
    group: string;
    level: number;
    title: string;
    type: string;
    uri: string;
    estimate_time: number;
    total_task: number;
    author: string;
    assignment: {
      data: Assignment;
    };
  };
}
