export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  graphql_public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      graphql: {
        Args: {
          extensions?: Json
          operationName?: string
          query?: string
          variables?: Json
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
  public: {
    Tables: {
      award_recipients: {
        Row: {
          award_id: string
          firm_id: string | null
          id: string
          person_id: string | null
          project_name: string | null
          year: number | null
        }
        Insert: {
          award_id: string
          firm_id?: string | null
          id?: string
          person_id?: string | null
          project_name?: string | null
          year?: number | null
        }
        Update: {
          award_id?: string
          firm_id?: string | null
          id?: string
          person_id?: string | null
          project_name?: string | null
          year?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "award_recipients_award_id_fkey"
            columns: ["award_id"]
            isOneToOne: false
            referencedRelation: "awards"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "award_recipients_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "award_recipients_person_id_fkey"
            columns: ["person_id"]
            isOneToOne: false
            referencedRelation: "people"
            referencedColumns: ["id"]
          },
        ]
      }
      awards: {
        Row: {
          award_name: string
          category: string | null
          created_at: string
          id: string
          organization: string | null
          prestige: Database["public"]["Enums"]["prestige_tier"]
          slug: string
          year: number | null
        }
        Insert: {
          award_name: string
          category?: string | null
          created_at?: string
          id?: string
          organization?: string | null
          prestige?: Database["public"]["Enums"]["prestige_tier"]
          slug: string
          year?: number | null
        }
        Update: {
          award_name?: string
          category?: string | null
          created_at?: string
          id?: string
          organization?: string | null
          prestige?: Database["public"]["Enums"]["prestige_tier"]
          slug?: string
          year?: number | null
        }
        Relationships: []
      }
      enrichment_queue: {
        Row: {
          attempts: number
          created_at: string
          enriched_at: string | null
          entity_id: string
          entity_type: Database["public"]["Enums"]["entity_type"]
          id: string
          last_error: string | null
          status: Database["public"]["Enums"]["queue_status"]
        }
        Insert: {
          attempts?: number
          created_at?: string
          enriched_at?: string | null
          entity_id: string
          entity_type: Database["public"]["Enums"]["entity_type"]
          id?: string
          last_error?: string | null
          status?: Database["public"]["Enums"]["queue_status"]
        }
        Update: {
          attempts?: number
          created_at?: string
          enriched_at?: string | null
          entity_id?: string
          entity_type?: Database["public"]["Enums"]["entity_type"]
          id?: string
          last_error?: string | null
          status?: Database["public"]["Enums"]["queue_status"]
        }
        Relationships: []
      }
      entity_aliases: {
        Row: {
          alias: string
          alias_normalized: string
          created_at: string
          entity_id: string
          entity_type: Database["public"]["Enums"]["entity_type"]
          id: string
        }
        Insert: {
          alias: string
          alias_normalized: string
          created_at?: string
          entity_id: string
          entity_type: Database["public"]["Enums"]["entity_type"]
          id?: string
        }
        Update: {
          alias?: string
          alias_normalized?: string
          created_at?: string
          entity_id?: string
          entity_type?: Database["public"]["Enums"]["entity_type"]
          id?: string
        }
        Relationships: []
      }
      firm_people: {
        Row: {
          firm_id: string
          id: string
          is_current: boolean
          person_id: string
          role: string | null
        }
        Insert: {
          firm_id: string
          id?: string
          is_current?: boolean
          person_id: string
          role?: string | null
        }
        Update: {
          firm_id?: string
          id?: string
          is_current?: boolean
          person_id?: string
          role?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "firm_people_firm_id_fkey"
            columns: ["firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "firm_people_person_id_fkey"
            columns: ["person_id"]
            isOneToOne: false
            referencedRelation: "people"
            referencedColumns: ["id"]
          },
        ]
      }
      firms: {
        Row: {
          canonical_name: string
          city: string | null
          country: string | null
          created_at: string
          display_name: string
          founded_year: number | null
          id: string
          merged_into: string | null
          sector: Database["public"]["Enums"]["sector_type"]
          short_description: string | null
          size_range: string | null
          slug: string
          updated_at: string
          website: string | null
        }
        Insert: {
          canonical_name: string
          city?: string | null
          country?: string | null
          created_at?: string
          display_name: string
          founded_year?: number | null
          id?: string
          merged_into?: string | null
          sector?: Database["public"]["Enums"]["sector_type"]
          short_description?: string | null
          size_range?: string | null
          slug: string
          updated_at?: string
          website?: string | null
        }
        Update: {
          canonical_name?: string
          city?: string | null
          country?: string | null
          created_at?: string
          display_name?: string
          founded_year?: number | null
          id?: string
          merged_into?: string | null
          sector?: Database["public"]["Enums"]["sector_type"]
          short_description?: string | null
          size_range?: string | null
          slug?: string
          updated_at?: string
          website?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "firms_merged_into_fkey"
            columns: ["merged_into"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
      ingest_cursors: {
        Row: {
          entity_count: number | null
          errors: Json | null
          last_cursor: string | null
          last_run_at: string | null
          source_name: string
          status: string | null
        }
        Insert: {
          entity_count?: number | null
          errors?: Json | null
          last_cursor?: string | null
          last_run_at?: string | null
          source_name: string
          status?: string | null
        }
        Update: {
          entity_count?: number | null
          errors?: Json | null
          last_cursor?: string | null
          last_run_at?: string | null
          source_name?: string
          status?: string | null
        }
        Relationships: []
      }
      people: {
        Row: {
          bio: string | null
          canonical_name: string
          created_at: string
          current_firm_id: string | null
          display_name: string
          id: string
          nationality: string | null
          role: string | null
          sector: Database["public"]["Enums"]["sector_type"]
          slug: string
          title: string | null
          updated_at: string
        }
        Insert: {
          bio?: string | null
          canonical_name: string
          created_at?: string
          current_firm_id?: string | null
          display_name: string
          id?: string
          nationality?: string | null
          role?: string | null
          sector?: Database["public"]["Enums"]["sector_type"]
          slug: string
          title?: string | null
          updated_at?: string
        }
        Update: {
          bio?: string | null
          canonical_name?: string
          created_at?: string
          current_firm_id?: string | null
          display_name?: string
          id?: string
          nationality?: string | null
          role?: string | null
          sector?: Database["public"]["Enums"]["sector_type"]
          slug?: string
          title?: string | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "people_current_firm_id_fkey"
            columns: ["current_firm_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
        ]
      }
      review_queue: {
        Row: {
          candidate_name: string
          confidence: number | null
          created_at: string
          entity_type: Database["public"]["Enums"]["entity_type"]
          id: string
          match_type: string | null
          notes: string | null
          resolved_at: string | null
          status: Database["public"]["Enums"]["review_status"]
          suggested_entity_id: string | null
        }
        Insert: {
          candidate_name: string
          confidence?: number | null
          created_at?: string
          entity_type: Database["public"]["Enums"]["entity_type"]
          id?: string
          match_type?: string | null
          notes?: string | null
          resolved_at?: string | null
          status?: Database["public"]["Enums"]["review_status"]
          suggested_entity_id?: string | null
        }
        Update: {
          candidate_name?: string
          confidence?: number | null
          created_at?: string
          entity_type?: Database["public"]["Enums"]["entity_type"]
          id?: string
          match_type?: string | null
          notes?: string | null
          resolved_at?: string | null
          status?: Database["public"]["Enums"]["review_status"]
          suggested_entity_id?: string | null
        }
        Relationships: []
      }
      sources: {
        Row: {
          author: string | null
          created_at: string
          id: string
          published_at: string | null
          sector: Database["public"]["Enums"]["sector_type"] | null
          source_name: string
          source_type: Database["public"]["Enums"]["source_type"]
          title: string
          url: string | null
        }
        Insert: {
          author?: string | null
          created_at?: string
          id?: string
          published_at?: string | null
          sector?: Database["public"]["Enums"]["sector_type"] | null
          source_name: string
          source_type?: Database["public"]["Enums"]["source_type"]
          title: string
          url?: string | null
        }
        Update: {
          author?: string | null
          created_at?: string
          id?: string
          published_at?: string | null
          sector?: Database["public"]["Enums"]["sector_type"] | null
          source_name?: string
          source_type?: Database["public"]["Enums"]["source_type"]
          title?: string
          url?: string | null
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      daitch_mokotoff: { Args: { "": string }; Returns: string[] }
      dmetaphone: { Args: { "": string }; Returns: string }
      dmetaphone_alt: { Args: { "": string }; Returns: string }
      show_limit: { Args: never; Returns: number }
      show_trgm: { Args: { "": string }; Returns: string[] }
      soundex: { Args: { "": string }; Returns: string }
      text_soundex: { Args: { "": string }; Returns: string }
      unaccent: { Args: { "": string }; Returns: string }
    }
    Enums: {
      entity_type: "firm" | "person"
      prestige_tier: "1" | "2" | "3"
      queue_status: "pending" | "processing" | "done" | "failed"
      review_status: "pending" | "accepted" | "rejected" | "skipped"
      sector_type:
        | "architecture"
        | "design"
        | "technology"
        | "multidisciplinary"
      source_type: "rss" | "crawl" | "api" | "manual" | "wikipedia"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  graphql_public: {
    Enums: {},
  },
  public: {
    Enums: {
      entity_type: ["firm", "person"],
      prestige_tier: ["1", "2", "3"],
      queue_status: ["pending", "processing", "done", "failed"],
      review_status: ["pending", "accepted", "rejected", "skipped"],
      sector_type: [
        "architecture",
        "design",
        "technology",
        "multidisciplinary",
      ],
      source_type: ["rss", "crawl", "api", "manual", "wikipedia"],
    },
  },
} as const

