CREATE TABLE "candidate_agent_reviews" (
	"id" text PRIMARY KEY NOT NULL,
	"candidate_id" text NOT NULL,
	"model" text NOT NULL,
	"prompt_version" text NOT NULL,
	"verdict" text NOT NULL,
	"review_json" jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "candidate_categories" (
	"id" text PRIMARY KEY NOT NULL,
	"candidate_id" text NOT NULL,
	"category_key" text NOT NULL,
	"label" text NOT NULL,
	"raw_value" text NOT NULL,
	"display_order" integer NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "candidate_validations" (
	"id" text PRIMARY KEY NOT NULL,
	"candidate_id" text NOT NULL,
	"technical_valid" boolean NOT NULL,
	"dimension_valid" boolean NOT NULL,
	"transformation_valid" boolean NOT NULL,
	"diagnostics_json" jsonb NOT NULL,
	"issues_json" jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "puzzle_candidates" (
	"id" text PRIMARY KEY NOT NULL,
	"source_name" text NOT NULL,
	"source_dataset_id" text NOT NULL,
	"source_url" text,
	"topic" text NOT NULL,
	"title" text NOT NULL,
	"context" text,
	"geography" text,
	"time_period" text,
	"unit" text,
	"population_universe" text,
	"transformation_type" text NOT NULL,
	"transformation_metadata_json" jsonb NOT NULL,
	"source_metadata_json" jsonb NOT NULL,
	"raw_payload_json" jsonb NOT NULL,
	"status" text NOT NULL,
	"human_status" text,
	"human_notes" text,
	"reviewed_by" text,
	"reviewed_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "puzzles" ADD COLUMN "candidate_id" text;--> statement-breakpoint
ALTER TABLE "candidate_agent_reviews" ADD CONSTRAINT "candidate_agent_reviews_candidate_id_puzzle_candidates_id_fk" FOREIGN KEY ("candidate_id") REFERENCES "public"."puzzle_candidates"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "candidate_categories" ADD CONSTRAINT "candidate_categories_candidate_id_puzzle_candidates_id_fk" FOREIGN KEY ("candidate_id") REFERENCES "public"."puzzle_candidates"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "candidate_validations" ADD CONSTRAINT "candidate_validations_candidate_id_puzzle_candidates_id_fk" FOREIGN KEY ("candidate_id") REFERENCES "public"."puzzle_candidates"("id") ON DELETE cascade ON UPDATE no action;