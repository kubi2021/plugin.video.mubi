import {
    Body,
    Container,
    Head,
    Heading,
    Hr,
    Html,
    Img,
    Link,
    Preview,
    Section,
    Text,
    Button,
    Tailwind,
    Row,
    Column,
} from "@react-email/components";
import * as React from "react";
import * as fs from "fs";
import * as path from "path";

// Load actual data from generated JSON file
const loadDigestData = (): DigestData => {
    const jsonPath = "/Users/kubi/Documents/GitHub/plugin.video.mubi/tmp/weekly_digest.json";
    console.log("Loading JSON from:", jsonPath);

    try {
        const jsonContent = fs.readFileSync(jsonPath, "utf-8");
        const data = JSON.parse(jsonContent);
        console.log("Loaded movies count:", data.newArrivals?.length);
        return data;
    } catch (error) {
        console.error("Error loading JSON:", error);
        // Fallback to sample data if JSON not found
        return {
            generatedAt: "January 01, 2026",
            totalMovies: 2057,
            newArrivals: [
                {
                    title: "Senna (FALLBACK)",
                    year: 2010,
                    bayesian: 8.4,
                    mubi: 8.7,
                    imdb: 8.5,
                    tmdb: 8.1,
                    genres: ["Documentary", "Biography", "Sport"],
                    duration: 106,
                    countries: ["United Kingdom", "France"],
                    directors: ["Asif Kapadia"],
                    synopsis: "A Brazilian motor-racing legend, considered by many the greatest driver to ever live.",
                    imageUrl: "https://assets.mubicdn.net/images/film/37136/image-w448.jpg",
                    trailerUrl: "https://trailers.mubicdn.net/37136/optimised/720p-t-senna.mp4",
                },
            ],
        };
    }
};

const digestData = loadDigestData();
console.log("digestData.newArrivals.length =", digestData.newArrivals.length);

const formatVoters = (count: number) => {
    return new Intl.NumberFormat('en-US', {
        notation: "compact",
        compactDisplay: "short",
        maximumFractionDigits: 1
    }).format(count).toLowerCase();
};

const formatDateRange = (dateString: string) => {
    const endDate = new Date(dateString);
    const startDate = new Date(endDate);
    startDate.setDate(startDate.getDate() - 7);

    const options: Intl.DateTimeFormatOptions = { month: 'short', day: '2-digit' };
    const startStr = startDate.toLocaleDateString('en-US', options);
    const endStr = endDate.toLocaleDateString('en-US', options);

    return `${startStr} – ${endStr}`;
};

const formatAvailability = (dateString: string) => {
    const date = new Date(dateString);
    const options: Intl.DateTimeFormatOptions = { month: 'long', day: 'numeric', year: 'numeric' };
    return date.toLocaleDateString('en-US', options);
};

interface Movie {
    id?: number;
    imdbId?: string;
    tmdbId?: number;
    title: string;
    year: number;
    bayesian?: number;
    bayesianVoters?: number;
    mubi?: number;
    mubiVoters?: number;
    imdb?: number;
    imdbVoters?: number;
    tmdb?: number;
    tmdbVoters?: number;
    genres: string[];
    duration: number;
    countries: string[];
    directors: string[];
    synopsis: string;
    imageUrl?: string;
    trailerUrl?: string;
    availableUntil?: string;
}

interface DigestData {
    generatedAt: string;
    totalMovies: number;
    newArrivals: Movie[];
}

const formatRatings = (movie: Movie): string => {
    const parts: string[] = [];
    if (movie.bayesian) parts.push(`⭐ ${movie.bayesian.toFixed(1)}`);
    if (movie.mubi) parts.push(`Mubi: ${movie.mubi.toFixed(1)}`);
    if (movie.imdb) parts.push(`IMDb: ${movie.imdb.toFixed(1)}`);
    if (movie.tmdb) parts.push(`TMDB: ${movie.tmdb.toFixed(1)}`);
    return parts.join(" | ") || "No ratings";
};

export const WeeklyDigestEmail = ({ data = digestData }: { data?: DigestData }) => {
    return (
        <Html>
            <Head />
            <Preview>Kubi Weekly Digest - {data.newArrivals.length} new films this week!</Preview>
            <Tailwind>
                <Body className="bg-gray-100 font-sans">
                    <Container className="mx-auto my-[40px] max-w-[600px] rounded-[8px] bg-white p-0">
                        {/* Header */}
                        <Section className="rounded-t-[8px] bg-[#e91e63] px-[48px] py-[32px] text-center">
                            <Heading className="m-0 text-[28px] font-bold text-white tracking-tight">
                                Kubi Weekly Digest
                            </Heading>
                            <Text className="m-0 mt-[8px] text-[16px] text-gray-200 font-medium">
                                Just Added: {formatDateRange(data.generatedAt)}
                            </Text>
                        </Section>

                        {/* Stats Section */}
                        <Section className="px-[48px] py-[24px]">
                            <table className="w-full">
                                <tbody>
                                    <tr>
                                        <td className="w-1/2 align-top">
                                            <Text className="m-0 text-left text-[18px] leading-[24px] font-bold tracking-tight text-gray-900 tabular-nums">
                                                {data.totalMovies.toLocaleString()}
                                            </Text>
                                            <Text className="m-0 text-left text-[12px] leading-[18px] text-gray-500">
                                                Total Movies
                                            </Text>
                                        </td>
                                        <td className="w-1/2 align-top">
                                            <Text className="m-0 text-left text-[18px] leading-[24px] font-bold tracking-tight text-gray-900 tabular-nums">
                                                {data.newArrivals.length}
                                            </Text>
                                            <Text className="m-0 text-left text-[12px] leading-[18px] text-gray-500">
                                                New This Week
                                            </Text>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </Section>

                        <Hr className="my-[16px] border-gray-300 border-t-2" />

                        {/* Benefits Section */}
                        <Section className="my-[16px] px-[48px]">
                            <Row>
                                <Text className="mt-[8px] text-[16px] text-gray-500 leading-[24px]">
                                    For the optimal experience, view your movies within <Link href="https://kodi.tv/" className="text-[#e91e63] no-underline">Kodi</Link>, using the <Link href="https://github.com/kubi2021/plugin.video.mubi" className="text-[#e91e63] no-underline">Kubi plugin</Link>.
                                </Text>
                            </Row>
                            <Row className="mt-[16px]">
                                <Column align="center" className="w-1/3 pr-[12px] align-top">
                                    <Img
                                        alt="sync icon"
                                        height="48"
                                        src="https://img.icons8.com/ios-filled/50/e91e63/refresh.png"
                                        width="48"
                                    />
                                    <Text className="m-0 mt-[16px] font-semibold text-[20px] text-gray-900 leading-[24px]">
                                        Seamless Sync
                                    </Text>
                                    <Text className="mt-[8px] mb-0 text-[16px] text-gray-500 leading-[24px]">
                                        Sync and play Mubi movies directly in Kodi.
                                    </Text>
                                </Column>
                                <Column align="center" className="w-1/3 px-[12px] align-top">
                                    <Img
                                        alt="globe icon"
                                        height="48"
                                        src="https://img.icons8.com/ios-filled/50/e91e63/globe.png"
                                        width="48"
                                    />
                                    <Text className="m-0 mt-[16px] font-semibold text-[20px] text-gray-900 leading-[28px]">
                                        Global Access
                                    </Text>
                                    <Text className="mt-[8px] mb-0 text-[16px] text-gray-500 leading-[24px]">
                                        Access the worldwide Mubi catalogue (2k+ movies)
                                    </Text>
                                </Column>
                                <Column align="center" className="w-1/3 pl-[12px] align-top">
                                    <Img
                                        alt="AI icon"
                                        height="48"
                                        src="https://img.icons8.com/ios-filled/50/e91e63/sparkling.png"
                                        width="48"
                                    />
                                    <Text className="m-0 mt-[16px] font-semibold text-[20px] text-gray-900 leading-[28px]">
                                        Smart Ratings
                                    </Text>
                                    <Text className="mt-[8px] mb-0 text-[16px] text-gray-500 leading-[24px]">
                                        Use Mubi, IMDb, TMDB, and our composite rating to make your decision.
                                    </Text>
                                </Column>
                            </Row>
                        </Section>

                        <Section className="my-[16px] px-[48px]">
                            <Text className="mt-[24px] mb-[4px] font-semibold text-[14px] text-gray-900 uppercase tracking-wider">
                                Disclaimer
                            </Text>
                            <ul className="m-0 pl-[20px]">
                                <li className="text-[13px] text-gray-500 leading-[20px] mb-[4px]">
                                    Not all movies are available in all countries; you will figure out the available country at the time of playing the movie in Kodi.
                                </li>
                                <li className="text-[13px] text-gray-500 leading-[20px]">
                                    If the movie is not available in your country, you will need a VPN and connect to one of the available countries.
                                </li>
                            </ul>
                        </Section>

                        <Hr className="my-[16px] border-gray-300 border-t-2" />
                        <Section className="px-[48px] py-[24px]">
                            {data.newArrivals.map((movie, index) => (
                                <Section key={index} className="my-[16px]">
                                    <Heading as="h2" className="text-left">
                                        {index + 1}.{' '}
                                        {movie.id ? (
                                            <Link
                                                href={`https://mubi.com/films/${movie.id}`}
                                                className="text-gray-900 no-underline"
                                            >
                                                {movie.title}
                                            </Link>
                                        ) : (
                                            movie.title
                                        )}{' '}
                                        <span className="text-gray-500 font-normal">({movie.year})</span>
                                    </Heading>

                                    <Text className="m-0 mt-[4px] text-[13px] leading-[20px] text-gray-500">
                                        <span className="font-semibold text-gray-900">{movie.genres.join(", ")}</span>
                                        <span className="mx-[8px] text-gray-300">|</span>
                                        {movie.duration} min
                                        {movie.countries.length > 0 && (
                                            <>
                                                <span className="mx-[8px] text-gray-300">|</span>
                                                {movie.countries.join(", ")}
                                            </>
                                        )}
                                    </Text>

                                    {movie.directors.length > 0 && (
                                        <Text className="m-0 mt-[4px] text-[13px] text-gray-500">
                                            Director <span className="font-semibold text-gray-900">{movie.directors.join(", ")}</span>
                                        </Text>
                                    )}

                                    {movie.imageUrl && (
                                        <Img
                                            alt={movie.title}
                                            className="mt-[12px] w-full rounded-[8px] object-cover"
                                            height={280}
                                            src={movie.imageUrl}
                                        />
                                    )}

                                    <div className="mt-[4px]">
                                        {(() => {
                                            const ratings = [];
                                            if (movie.bayesian && movie.bayesian > 0) ratings.push({ label: 'Composite', value: movie.bayesian, voters: movie.bayesianVoters });
                                            if (movie.mubi && movie.mubi > 0) ratings.push({ label: 'Mubi', value: movie.mubi, voters: movie.mubiVoters });
                                            if (movie.imdb && movie.imdb > 0) ratings.push({ label: 'IMDb', value: movie.imdb, voters: movie.imdbVoters });
                                            if (movie.tmdb && movie.tmdb > 0) ratings.push({ label: 'TMDB', value: movie.tmdb, voters: movie.tmdbVoters });

                                            if (ratings.length === 0) {
                                                return (
                                                    <Row>
                                                        <Column className="align-top">
                                                            <Text className="m-0 text-left text-[14px] text-gray-500 italic pb-[8px]">
                                                                No ratings available
                                                            </Text>
                                                        </Column>
                                                    </Row>
                                                );
                                            }

                                            const rows = [];
                                            for (let i = 0; i < ratings.length; i += 2) {
                                                rows.push(ratings.slice(i, i + 2));
                                            }

                                            return rows.map((row, rowIndex) => (
                                                <Row key={rowIndex}>
                                                    {row.map((rating) => {
                                                        const content = (
                                                            <>
                                                                <Text className="m-0 text-left text-[18px] leading-[24px] font-bold tracking-tight text-gray-900 tabular-nums">
                                                                    {rating.value.toFixed(1)} {rating.voters ? <span className="text-[14px] font-normal text-gray-400">({formatVoters(rating.voters)})</span> : null}
                                                                </Text>
                                                                <Text className="m-0 text-left text-[12px] leading-[18px] text-gray-500">
                                                                    {rating.label}
                                                                </Text>
                                                            </>
                                                        );

                                                        return (
                                                            <Column key={rating.label} className="w-1/2 align-top pb-[8px]">
                                                                {rating.label === 'Mubi' && movie.id ? (
                                                                    <Link href={`https://mubi.com/films/${movie.id}`} className="no-underline text-inherit block">
                                                                        {content}
                                                                    </Link>
                                                                ) : rating.label === 'IMDb' && movie.imdbId ? (
                                                                    <Link href={`https://www.imdb.com/title/${movie.imdbId}/`} className="no-underline text-inherit block">
                                                                        {content}
                                                                    </Link>
                                                                ) : rating.label === 'TMDB' && movie.tmdbId ? (
                                                                    <Link href={`https://www.themoviedb.org/movie/${movie.tmdbId}`} className="no-underline text-inherit block">
                                                                        {content}
                                                                    </Link>
                                                                ) : (
                                                                    content
                                                                )}
                                                            </Column>
                                                        );
                                                    })}
                                                </Row>
                                            ));
                                        })()}
                                    </div>

                                    <Text className="m-0 mt-[8px] text-[14px] leading-[22px] text-gray-600">
                                        {movie.synopsis}
                                    </Text>

                                    {movie.availableUntil && (
                                        <Text className="m-0 mt-[12px] text-[13px] text-gray-400 font-light">
                                            Available until <span className="font-bold">{formatAvailability(movie.availableUntil)}</span>
                                        </Text>
                                    )}

                                    {movie.trailerUrl && (
                                        <Button
                                            className="mt-[8px] rounded-[8px] bg-[#e91e63] px-[16px] py-[10px] text-center text-[14px] font-semibold text-white"
                                            href={movie.trailerUrl}
                                        >
                                            Watch Trailer
                                        </Button>
                                    )}


                                </Section>
                            ))}
                        </Section>

                        {/* Footer */}
                        <Section className="rounded-b-[8px] bg-gray-50 px-[48px] py-[24px] text-center">
                            <Text className="m-0 text-[12px] text-gray-400">
                                This digest was generated automatically from the Mubi catalog.
                            </Text>
                        </Section>
                    </Container>
                </Body>
            </Tailwind>
        </Html >
    );
};

export default function WeeklyDigestEmailPreview() {
    const data = loadDigestData();
    return <WeeklyDigestEmail digestData={data} />;
}
