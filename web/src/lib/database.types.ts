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
      education: {
        Row: {
          created_at: string
          degree: string | null
          end_year: number | null
          field: string | null
          id: string
          institution_id: string | null
          institution_name: string
          person_id: string
          source: string | null
          start_year: number | null
        }
        Insert: {
          created_at?: string
          degree?: string | null
          end_year?: number | null
          field?: string | null
          id?: string
          institution_id?: string | null
          institution_name: string
          person_id: string
          source?: string | null
          start_year?: number | null
        }
        Update: {
          created_at?: string
          degree?: string | null
          end_year?: number | null
          field?: string | null
          id?: string
          institution_id?: string | null
          institution_name?: string
          person_id?: string
          source?: string | null
          start_year?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "education_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "firms"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "education_person_id_fkey"
            columns: ["person_id"]
            isOneToOne: false
            referencedRelation: "people"
            referencedColumns: ["id"]
          },
        ]
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
      entity_relationships: {
        Row: {
          created_at: string
          end_year: number | null
          from_entity_id: string
          from_entity_type: Database["public"]["Enums"]["entity_type"]
          id: string
          notes: string | null
          relationship: Database["public"]["Enums"]["relationship_type"]
          start_year: number | null
          to_entity_id: string
          to_entity_type: Database["public"]["Enums"]["entity_type"]
        }
        Insert: {
          created_at?: string
          end_year?: number | null
          from_entity_id: string
          from_entity_type: Database["public"]["Enums"]["entity_type"]
          id?: string
          notes?: string | null
          relationship: Database["public"]["Enums"]["relationship_type"]
          start_year?: number | null
          to_entity_id: string
          to_entity_type: Database["public"]["Enums"]["entity_type"]
        }
        Update: {
          created_at?: string
          end_year?: number | null
          from_entity_id?: string
          from_entity_type?: Database["public"]["Enums"]["entity_type"]
          id?: string
          notes?: string | null
          relationship?: Database["public"]["Enums"]["relationship_type"]
          start_year?: number | null
          to_entity_id?: string
          to_entity_type?: Database["public"]["Enums"]["entity_type"]
        }
        Relationships: []
      }
      entity_sources: {
        Row: {
          confidence: number
          created_at: string
          entity_id: string
          entity_type: Database["public"]["Enums"]["entity_type"]
          id: string
          mention_type: string
          source_id: string
        }
        Insert: {
          confidence?: number
          created_at?: string
          entity_id: string
          entity_type: Database["public"]["Enums"]["entity_type"]
          id?: string
          mention_type?: string
          source_id: string
        }
        Update: {
          confidence?: number
          created_at?: string
          entity_id?: string
          entity_type?: Database["public"]["Enums"]["entity_type"]
          id?: string
          mention_type?: string
          source_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "entity_sources_source_id_fkey"
            columns: ["source_id"]
            isOneToOne: false
            referencedRelation: "sources"
            referencedColumns: ["id"]
          },
        ]
      }
      entity_tags: {
        Row: {
          created_at: string
          entity_id: string
          entity_type: Database["public"]["Enums"]["entity_type"]
          id: string
          source: string
          tag_id: string
        }
        Insert: {
          created_at?: string
          entity_id: string
          entity_type: Database["public"]["Enums"]["entity_type"]
          id?: string
          source?: string
          tag_id: string
        }
        Update: {
          created_at?: string
          entity_id?: string
          entity_type?: Database["public"]["Enums"]["entity_type"]
          id?: string
          source?: string
          tag_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "entity_tags_tag_id_fkey"
            columns: ["tag_id"]
            isOneToOne: false
            referencedRelation: "tags"
            referencedColumns: ["id"]
          },
        ]
      }
      firm_people: {
        Row: {
          end_year: number | null
          firm_id: string
          id: string
          is_current: boolean
          person_id: string
          role: string | null
          source: string | null
          start_year: number | null
        }
        Insert: {
          end_year?: number | null
          firm_id: string
          id?: string
          is_current?: boolean
          person_id: string
          role?: string | null
          source?: string | null
          start_year?: number | null
        }
        Update: {
          end_year?: number | null
          firm_id?: string
          id?: string
          is_current?: boolean
          person_id?: string
          role?: string | null
          source?: string | null
          start_year?: number | null
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
          country_code: string | null
          created_at: string
          display_name: string
          founded_year: number | null
          id: string
          image_url: string | null
          last_seen_at: string | null
          latitude: number | null
          logo_url: string | null
          longitude: number | null
          merged_into: string | null
          openalex_id: string | null
          publish_status: string
          quality_score: number
          sector: Database["public"]["Enums"]["sector_type"]
          short_description: string | null
          size_range: string | null
          slug: string
          source_count: number
          updated_at: string
          website: string | null
          wikidata_id: string | null
        }
        Insert: {
          canonical_name: string
          city?: string | null
          country?: string | null
          country_code?: string | null
          created_at?: string
          display_name: string
          founded_year?: number | null
          id?: string
          image_url?: string | null
          last_seen_at?: string | null
          latitude?: number | null
          logo_url?: string | null
          longitude?: number | null
          merged_into?: string | null
          openalex_id?: string | null
          publish_status?: string
          quality_score?: number
          sector?: Database["public"]["Enums"]["sector_type"]
          short_description?: string | null
          size_range?: string | null
          slug: string
          source_count?: number
          updated_at?: string
          website?: string | null
          wikidata_id?: string | null
        }
        Update: {
          canonical_name?: string
          city?: string | null
          country?: string | null
          country_code?: string | null
          created_at?: string
          display_name?: string
          founded_year?: number | null
          id?: string
          image_url?: string | null
          last_seen_at?: string | null
          latitude?: number | null
          logo_url?: string | null
          longitude?: number | null
          merged_into?: string | null
          openalex_id?: string | null
          publish_status?: string
          quality_score?: number
          sector?: Database["public"]["Enums"]["sector_type"]
          short_description?: string | null
          size_range?: string | null
          slug?: string
          source_count?: number
          updated_at?: string
          website?: string | null
          wikidata_id?: string | null
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
          birth_year: number | null
          canonical_name: string
          created_at: string
          current_firm_id: string | null
          death_year: number | null
          display_name: string
          id: string
          image_url: string | null
          last_seen_at: string | null
          nationality: string | null
          openalex_id: string | null
          orcid: string | null
          publish_status: string
          quality_score: number
          role: string | null
          sector: Database["public"]["Enums"]["sector_type"]
          slug: string
          source_count: number
          title: string | null
          updated_at: string
          wikidata_id: string | null
        }
        Insert: {
          bio?: string | null
          birth_year?: number | null
          canonical_name: string
          created_at?: string
          current_firm_id?: string | null
          death_year?: number | null
          display_name: string
          id?: string
          image_url?: string | null
          last_seen_at?: string | null
          nationality?: string | null
          openalex_id?: string | null
          orcid?: string | null
          publish_status?: string
          quality_score?: number
          role?: string | null
          sector?: Database["public"]["Enums"]["sector_type"]
          slug: string
          source_count?: number
          title?: string | null
          updated_at?: string
          wikidata_id?: string | null
        }
        Update: {
          bio?: string | null
          birth_year?: number | null
          canonical_name?: string
          created_at?: string
          current_firm_id?: string | null
          death_year?: number | null
          display_name?: string
          id?: string
          image_url?: string | null
          last_seen_at?: string | null
          nationality?: string | null
          openalex_id?: string | null
          orcid?: string | null
          publish_status?: string
          quality_score?: number
          role?: string | null
          sector?: Database["public"]["Enums"]["sector_type"]
          slug?: string
          source_count?: number
          title?: string | null
          updated_at?: string
          wikidata_id?: string | null
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
      pipeline_runs: {
        Row: {
          failures: number
          finished_at: string | null
          id: string
          sources_run: Json
          started_at: string
          summary: Json | null
          total_entities: number
          webhook_sent: boolean
        }
        Insert: {
          failures?: number
          finished_at?: string | null
          id?: string
          sources_run?: Json
          started_at?: string
          summary?: Json | null
          total_entities?: number
          webhook_sent?: boolean
        }
        Update: {
          failures?: number
          finished_at?: string | null
          id?: string
          sources_run?: Json
          started_at?: string
          summary?: Json | null
          total_entities?: number
          webhook_sent?: boolean
        }
        Relationships: []
      }
      project_entities: {
        Row: {
          created_at: string
          entity_id: string
          entity_type: Database["public"]["Enums"]["entity_type"]
          id: string
          project_id: string
          role: string | null
        }
        Insert: {
          created_at?: string
          entity_id: string
          entity_type: Database["public"]["Enums"]["entity_type"]
          id?: string
          project_id: string
          role?: string | null
        }
        Update: {
          created_at?: string
          entity_id?: string
          entity_type?: Database["public"]["Enums"]["entity_type"]
          id?: string
          project_id?: string
          role?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "project_entities_project_id_fkey"
            columns: ["project_id"]
            isOneToOne: false
            referencedRelation: "projects"
            referencedColumns: ["id"]
          },
        ]
      }
      projects: {
        Row: {
          city: string | null
          country: string | null
          created_at: string
          description: string | null
          display_name: string
          id: string
          image_url: string | null
          latitude: number | null
          location: string | null
          longitude: number | null
          project_type: Database["public"]["Enums"]["project_type"]
          sector: Database["public"]["Enums"]["sector_type"] | null
          slug: string
          updated_at: string
          wikidata_id: string | null
          year: number | null
        }
        Insert: {
          city?: string | null
          country?: string | null
          created_at?: string
          description?: string | null
          display_name: string
          id?: string
          image_url?: string | null
          latitude?: number | null
          location?: string | null
          longitude?: number | null
          project_type?: Database["public"]["Enums"]["project_type"]
          sector?: Database["public"]["Enums"]["sector_type"] | null
          slug: string
          updated_at?: string
          wikidata_id?: string | null
          year?: number | null
        }
        Update: {
          city?: string | null
          country?: string | null
          created_at?: string
          description?: string | null
          display_name?: string
          id?: string
          image_url?: string | null
          latitude?: number | null
          location?: string | null
          longitude?: number | null
          project_type?: Database["public"]["Enums"]["project_type"]
          sector?: Database["public"]["Enums"]["sector_type"] | null
          slug?: string
          updated_at?: string
          wikidata_id?: string | null
          year?: number | null
        }
        Relationships: []
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
      tags: {
        Row: {
          category: string | null
          created_at: string
          id: string
          name: string
          slug: string
        }
        Insert: {
          category?: string | null
          created_at?: string
          id?: string
          name: string
          slug: string
        }
        Update: {
          category?: string | null
          created_at?: string
          id?: string
          name?: string
          slug?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      count_awards_by_organization: {
        Args: never
        Returns: {
          count: number
          organization: string
        }[]
      }
      count_firms_by_country: {
        Args: never
        Returns: {
          count: number
          country: string
        }[]
      }
      count_firms_by_sector: {
        Args: never
        Returns: {
          count: number
          sector: Database["public"]["Enums"]["sector_type"]
        }[]
      }
      count_people_by_role: {
        Args: never
        Returns: {
          count: number
          role: string
        }[]
      }
      daitch_mokotoff: { Args: { "": string }; Returns: string[] }
      dmetaphone: { Args: { "": string }; Returns: string }
      dmetaphone_alt: { Args: { "": string }; Returns: string }
      get_people_letters: {
        Args: never
        Returns: {
          letter: string
        }[]
      }
      match_entity_trigram: {
        Args: { search_name: string; search_type: string; threshold?: number }
        Returns: {
          canonical_name: string
          id: string
          similarity: number
        }[]
      }
      search_directory: {
        Args: {
          country_filter?: string
          query: string
          result_limit?: number
          sector_filter?: string
        }
        Returns: {
          city: string
          country: string
          display_name: string
          entity_type: string
          id: string
          rank: number
          role: string
          sector: string
          short_description: string
          slug: string
        }[]
      }
      show_limit: { Args: never; Returns: number }
      show_trgm: { Args: { "": string }; Returns: string[] }
      soundex: { Args: { "": string }; Returns: string }
      text_soundex: { Args: { "": string }; Returns: string }
      unaccent: { Args: { "": string }; Returns: string }
      upsert_entity_with_aliases: {
        Args: {
          p_aliases?: Json
          p_canonical_name: string
          p_city?: string
          p_country?: string
          p_display_name: string
          p_entity_type: string
          p_openalex_id?: string
          p_sector: string
          p_slug: string
          p_website?: string
          p_wikidata_id?: string
        }
        Returns: Json
      }
    }
    Enums: {
      entity_type: "firm" | "person"
      prestige_tier: "1" | "2" | "3"
      project_type:
        | "building"
        | "installation"
        | "research"
        | "product"
        | "exhibition"
        | "other"
      queue_status: "pending" | "processing" | "done" | "failed"
      relationship_type:
        | "subsidiary"
        | "partner"
        | "successor"
        | "spin_off"
        | "acquired_by"
        | "collaboration"
        | "other"
      review_status: "pending" | "accepted" | "rejected" | "skipped"
      sector_type:
        | "architecture"
        | "design"
        | "technology"
        | "multidisciplinary"
      source_type:
        | "rss"
        | "crawl"
        | "api"
        | "manual"
        | "wikipedia"
        | "repository"
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
      project_type: [
        "building",
        "installation",
        "research",
        "product",
        "exhibition",
        "other",
      ],
      queue_status: ["pending", "processing", "done", "failed"],
      relationship_type: [
        "subsidiary",
        "partner",
        "successor",
        "spin_off",
        "acquired_by",
        "collaboration",
        "other",
      ],
      review_status: ["pending", "accepted", "rejected", "skipped"],
      sector_type: [
        "architecture",
        "design",
        "technology",
        "multidisciplinary",
      ],
      source_type: ["rss", "crawl", "api", "manual", "wikipedia", "repository"],
    },
  },
} as const

