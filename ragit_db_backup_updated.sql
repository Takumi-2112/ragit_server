--
-- PostgreSQL database dump
--

-- Dumped from database version 14.17 (Homebrew)
-- Dumped by pg_dump version 14.17 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_username_key;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_pkey;
ALTER TABLE IF EXISTS ONLY public.users DROP CONSTRAINT IF EXISTS users_email_key;
ALTER TABLE IF EXISTS public.users ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.users_id_seq;
DROP TABLE IF EXISTS public.users;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: users; Type: TABLE; Schema: public; Owner: tommy
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(100) NOT NULL,
    password_hash character varying(255) NOT NULL,
    vectorstore_path character varying(255) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.users OWNER TO tommy;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: tommy
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO tommy;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: tommy
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: tommy
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: tommy
--

COPY public.users (id, username, email, password_hash, vectorstore_path, created_at, updated_at) FROM stdin;
1	TEST1	test@1.com	scrypt:32768:8:1$bqCEyrDJvA9eAGYr$0cfdd8934ca1f5f02fa1138fe62cf0d47f53b7c594d0e0cf13c2806cd6c07c1d96ea7c0b442776ddab261430c17a839c916baa8dbb366a80916b6410b93c4cd2	db/vectorstores/user_1_vectorstore	2025-08-06 16:04:59.873819	2025-08-06 16:04:59.873819
2	TEST2	test@2.com	scrypt:32768:8:1$HrE7E6jffKmIe2Vq$21eed08b34e222758b99778163379d3120e6fadfbdaa9aef93d049188840d5397c7d5d9bb61a070e5a29d45c56e4402ed4f10f9c6453243f01085db323d18636	db/vectorstores/user_2_vectorstore	2025-08-08 13:24:12.28336	2025-08-08 13:24:12.28336
3	nickthedick	nick@dick.com	scrypt:32768:8:1$jidecNIzp90py7Td$31b0d5a241e7cad914d11e6e03b9375f53ce942cf94b80db484f4c340d26935ed9ac045411dd8242ef90e1da9858bca326c021c5ed91fe8fad2646fd8e12fb53	db/vectorstores/user_3_vectorstore	2025-08-09 22:23:29.106547	2025-08-09 22:23:29.106547
\.


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: tommy
--

SELECT pg_catalog.setval('public.users_id_seq', 3, true);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: tommy
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: tommy
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: tommy
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- PostgreSQL database dump complete
--

