CREATE TABLE "game_results" (
	"id" text PRIMARY KEY NOT NULL,
	"player_id" text NOT NULL,
	"puzzle_id" text NOT NULL,
	"started_at" timestamp with time zone DEFAULT now() NOT NULL,
	"completed_at" timestamp with time zone,
	"solved" boolean DEFAULT false NOT NULL,
	"attempt_count" integer DEFAULT 0 NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "game_results_player_id_puzzle_id_unique" UNIQUE("player_id","puzzle_id")
);
--> statement-breakpoint
CREATE TABLE "guesses" (
	"id" text PRIMARY KEY NOT NULL,
	"game_result_id" text NOT NULL,
	"attempt_number" integer NOT NULL,
	"assignments_json" jsonb NOT NULL,
	"correct_positions_json" jsonb NOT NULL,
	"correct_count" integer NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "guesses_game_result_id_attempt_number_unique" UNIQUE("game_result_id","attempt_number")
);
--> statement-breakpoint
CREATE TABLE "puzzle_categories" (
	"id" text PRIMARY KEY NOT NULL,
	"puzzle_id" text NOT NULL,
	"category_key" text NOT NULL,
	"label" text NOT NULL,
	"raw_value" text NOT NULL,
	"slice_order" integer NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "puzzles" (
	"id" text PRIMARY KEY NOT NULL,
	"slug" text NOT NULL,
	"title" text NOT NULL,
	"context" text,
	"max_attempts" integer NOT NULL,
	"status" text NOT NULL,
	"publish_date" date NOT NULL,
	"source_name" text,
	"source_url" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "puzzles_slug_unique" UNIQUE("slug")
);
--> statement-breakpoint
ALTER TABLE "game_results" ADD CONSTRAINT "game_results_puzzle_id_puzzles_id_fk" FOREIGN KEY ("puzzle_id") REFERENCES "public"."puzzles"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "guesses" ADD CONSTRAINT "guesses_game_result_id_game_results_id_fk" FOREIGN KEY ("game_result_id") REFERENCES "public"."game_results"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "puzzle_categories" ADD CONSTRAINT "puzzle_categories_puzzle_id_puzzles_id_fk" FOREIGN KEY ("puzzle_id") REFERENCES "public"."puzzles"("id") ON DELETE cascade ON UPDATE no action;