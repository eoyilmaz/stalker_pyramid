const webpack = require("webpack");
const path = require("path");
const ExtractTextPlugin = require("extract-text-webpack-plugin");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const devMode = process.env.NODE_ENV !== 'production';



const config = {
    entry: path.resolve('src', 'index.ts'),
    plugins: [
        new MiniCssExtractPlugin({
            // Options similar to the same options in webpackOptions.output
            // both options are optional
            filename: "css/stalker.css",  // devMode ? '[name].css': '[name].[hash].css',
            chunkFilename: "css/[id].css",  // devMode ? '[id].css': '[id].[hash].css',
        })
    ],
    module: {
        rules: [
            {
                test: require.resolve('jquery'),
                loader: "expose-loader",
                options: {
                    exposes: ["$", "jQuery"],
                }
            },
            {
                test: /\.js$/,
                enforce: "pre",
                use: ["source-map-loader"],
            },
            {
                test: /\.tsx?$/,
                use: 'ts-loader',
                exclude: /node_modules/
            },
            {
                test: /\.(png|jpg|gif)$/i,
                use: [
                    {
                        loader: 'url-loader',
                        options: {
                            limit: 81920,
                            fallback: 'file-loader'
                        }
                    }
                ]
            },
            {
                test: /\.(woff|woff2|eot|ttf|otf)$/,
                loader: "file-loader",
                options: {
                    publicPath: '/static/',
                }
            },
            {
                test: /\.css$/,
                include: path.join(__dirname, 'src/css'),
                exclude: [
                    /\.(config|overrides|variables)$/,
                ],
                use: [
                    {
                        loader: 'style-loader',
                    },
                    // {
                    //     loader: MiniCssExtractPlugin.loader
                    // },
                    {
                        loader: "css-loader",
                        // options: { importLoaders: 1 }
                    },
                    // {
                    //     loader: 'typings-for-css-modules-loader',
                    //     options: {
                    //         modules: true,
                    //         namedExport: true,
                    //         camelCase: true,
                    //     }
                    // },
                ]
            },
            {
                test: /\.less$/,
                include: [
                    path.resolve(__dirname, 'src', 'less'),
                ],
                exclude: [
                    /\.(config|overrides|variables)$/,
                ],
                use: [
                    {
                        loader: 'style-loader' // creates style nodes from JS strings
                        // loader: MiniCssExtractPlugin.loader,
                    },
                    {
                        loader: 'css-loader', // translates CSS into CommonJS
                        // options: { importLoaders: 1 }
                    },
                    {
                        loader: 'less-loader', // compiles Less to CSS
                        options: {
                            paths: [
                                path.resolve(__dirname, 'src', 'less')
                            ],
                            javascriptEnabled: true,
                            url: false,
                            relativeUrls: true,
                        }
                    },
                ]
            }
        ]
    },
    resolve: {
        extensions: ['.tsx', '.ts', '.js', '.less', '.css']
    },
    output: {
        path: path.resolve(__dirname, '../stalker_pyramid/static'),
        filename: 'js/stalker.js',
        publicPath: "/",
    },
};

config.node = {
  fs: 'empty',
}

module.exports = config;