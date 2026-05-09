import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(const PrediApp());
}

class PrediApp extends StatelessWidget {
  const PrediApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'PREDI AI - Multi-Timeframe',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const PredictionScreen(),
    );
  }
}

class PredictionScreen extends StatefulWidget {
  const PredictionScreen({super.key});

  @override
  State<PredictionScreen> createState() => _PredictionScreenState();
}

class _PredictionScreenState extends State<PredictionScreen> {
  // Timeframe selection
  String selectedTimeframe = "M15";
  String selectedTicker = "GC=F";
  
  // Data display
  String currentPrice = "--";
  String predictedPrice = "--";
  String recommendation = "--";
  String direction = "--";
  String timeHorizon = "--";
  bool isLoading = false;
  String errorMessage = "";

  // Available options
  final Map<String, String> timeframes = {
    "M15": "15-minute",
    "1H": "Hourly",
    "4H": "4-hourly",
  };

  // Full ticker list aligned with the backend ingestion scripts
  final List<String> tickers = [
    "GC=F", "SI=F", "CL=F", "NG=F",
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
    "AAPL", "MSFT",
  ];

  final Map<String, String> horizonMap = {
    "M15": "next 15 minutes",
    "1H": "next hour",
    "4H": "next 4 hours",
  };

  // วิ่งไปดึงข้อมูลจาก Railway API (ใช้งานได้ทุกแพลตฟอร์ม Web/iOS/Android)
  Future<void> fetchPrediction() async {
    setState(() {
      isLoading = true;
      errorMessage = "";
    });

    try {
      // 🚀 เปลี่ยนจาก 127.0.0.1 เป็นลิงก์ Railway ของคุณตรงนี้ครับ!
      final url = Uri.parse('https://bda-pro-production.up.railway.app/predict').replace(
        queryParameters: {
          'ticker': selectedTicker,
          'interval': selectedTimeframe,
        },
      );

      final response = await http.get(url);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);

        setState(() {
          currentPrice = data['current_price'].toString();
          predictedPrice = data['predicted_price'].toString();
          direction = data['direction']?.toString() ?? "--";
          recommendation = data['recommendation']?.toString() ?? "--";
          timeHorizon = data['time_horizon']?.toString() ?? horizonMap[selectedTimeframe] ?? "next period";
        });
      } else {
        String message = 'Server Error: ${response.statusCode}';
        try {
          final errorData = json.decode(response.body);
          if (errorData is Map && errorData['detail'] != null) {
            message = errorData['detail'].toString();
          }
        } catch (_) {}

        setState(() {
          errorMessage = message;
        });
      }
    } catch (e) {
      setState(() {
        errorMessage = "Connection error: ไม่สามารถเชื่อมต่อ Railway ได้ ($e)";
      });
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'PREDI - AI Predictor',
          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
        ),
        backgroundColor: Colors.deepPurple,
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ========== TIMEFRAME SELECTOR ==========
              const Text(
                '📊 Select Timeframe',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 10,
                children: timeframes.keys.map((tf) {
                  return ChoiceChip(
                    label: Text(timeframes[tf]!),
                    selected: selectedTimeframe == tf,
                    onSelected: (selected) {
                      setState(() => selectedTimeframe = tf);
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: 30),

              // ========== TICKER SELECTOR ==========
              const Text(
                '💰 Select Asset',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: tickers.map((ticker) {
                  return ChoiceChip(
                    label: Text(ticker),
                    selected: selectedTicker == ticker,
                    onSelected: (selected) {
                      setState(() => selectedTicker = ticker);
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: 30),

              // ========== CURRENT PRICE ==========
              Card(
                elevation: 4,
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Current Price (Now)',
                        style: TextStyle(fontSize: 16, color: Colors.grey),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        currentPrice == "--" ? currentPrice : '\$$currentPrice',
                        style: const TextStyle(fontSize: 36, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // ========== PREDICTED PRICE ==========
              Card(
                elevation: 4,
                color: Colors.deepPurple.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'AI Prediction ($timeHorizon)',
                        style: const TextStyle(
                          fontSize: 16,
                          color: Colors.deepPurple,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        predictedPrice == "--" ? predictedPrice : '\$$predictedPrice',
                        style: const TextStyle(
                          fontSize: 36,
                          fontWeight: FontWeight.bold,
                          color: Colors.deepPurple,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // ========== RECOMMENDATION ==========
              if (recommendation != "--")
                Card(
                  color: recommendation.contains("BUY")
                      ? Colors.green.shade50
                      : Colors.red.shade50,
                  child: Padding(
                    padding: const EdgeInsets.all(20.0),
                    child: Text(
                      recommendation,
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: recommendation.contains("BUY")
                            ? Colors.green
                            : Colors.red,
                      ),
                    ),
                  ),
                ),
              const SizedBox(height: 20),

              // ========== ERROR MESSAGE ==========
              if (errorMessage.isNotEmpty)
                Card(
                  color: Colors.red.shade50,
                  child: Padding(
                    padding: const EdgeInsets.all(15.0),
                    child: Text(
                      '⚠️ $errorMessage',
                      style: const TextStyle(color: Colors.red),
                    ),
                  ),
                ),
              const SizedBox(height: 30),

              // ========== FETCH BUTTON ==========
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.deepPurple,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: isLoading ? null : fetchPrediction,
                  child: isLoading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text(
                          'Get Prediction',
                          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}